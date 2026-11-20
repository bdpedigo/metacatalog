"""Render the local copy of the production Ray head pod configuration.

Run from the repository root:

    uv run --no-project --with pyyaml python -I local/materialize/render.py \
        --values-dir submodules/terraform-cave-private/ltv/ltv7/helmfile

The script reads the materialize release of a private helmfile folder, renders
the two configmaps of the local chart with `helm template --show-only`, and
writes these files to local/materialize/.rendered/ (mode 600):

- config.cfg  the chart config.cfg plus a local override block
- head.env    the env of the ray-head container, for docker compose
- proxy.env   the env of the cloudsql-proxy sidecar, for docker compose
- infra.env   the infrastructure names that the justfile recipes use

Secret values never pass through this script. The DB username and password go
to helm as placeholders, and the override block in config.cfg replaces them
from the environment of the container at run time. The script never calls
helmfile or vals, and it never renders the Secret objects of the chart.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHART = REPO_ROOT / "submodules/cave-helm-charts/charts/materializationengine"
DEFAULT_OUT = Path(__file__).resolve().parent / ".rendered"

USER_PLACEHOLDER = "__MAT_DB_USER__"
PASSWORD_PLACEHOLDER = "__MAT_DB_PASSWORD__"

CONFIG_MAP = "materializationengine-config"
RAY_CONFIG_MAP = "materializationengine-rayjob-template"

# The args of the rayCloudsqlProxy helper, except the instance name. compose.yaml
# repeats them. If the chart changes them, stop, so that the two cannot drift.
EXPECTED_PROXY_FLAGS = [
    "--port=3306",
    "--credentials-file=/secrets/cloudsql/google-secret.json",
    "--max-sigterm-delay=3600s",
]

# Python, because Flask executes config.cfg. Appended after the chart config.
OVERRIDE_BLOCK = f'''
# ---------------------------------------------------------------------------
# Local override block, appended by metacatalog/local/materialize/render.py.
# Everything above this line is the deployed config.cfg of the chart.
# ---------------------------------------------------------------------------
import os as _local_os
from urllib.parse import quote as _local_quote

# The credentials come from the container environment at run time.
SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
    "{USER_PLACEHOLDER}", _local_quote(_local_os.environ["MAT_DB_USER"], safe="")
).replace(
    "{PASSWORD_PLACEHOLDER}", _local_quote(_local_os.environ["MAT_DB_PASSWORD"], safe="")
)

# The local Redis service replaces the deployed Redis.
REDIS_HOST = "redis"
REDIS_PORT = "6379"
REDIS_PASSWORD = ""
REDIS_URL = "redis://redis:6379/0"
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

# Side effects of create_app() and of the scheduler stay off.
BEAT_SCHEDULES = []
STAGING_DATABASE_NAME = ""
MATERIALIZATION_UPLOAD_BUCKET_PATH = ""  # the CORS setup fails and is only logged
MATERIALIZATION_DUMP_BUCKET = "/exports"

# Output goes to local disk. All other DELTALAKE_* values stay at the deployed values.
DELTALAKE_OUTPUT_BUCKET = "/exports"

# configure_app() logs the full app config at DEBUG level, with the DB URI.
if LOGGING_LEVEL < logging.INFO:
    LOGGING_LEVEL = logging.INFO
'''


def fail(message: str) -> None:
    print(f"render.py: {message}", file=sys.stderr)
    sys.exit(1)


def require_gitignored(path: Path) -> None:
    """Stop unless git ignores the path. The path must exist."""
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "check-ignore", "-q", str(path)],
        check=False,
    )
    if result.returncode != 0:
        fail(f"git does not ignore {path}. Add it to .gitignore first.")


def write_private(path: Path, text: str) -> None:
    """Write a file with mode 600. An existing file gets mode 600 too."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(text)


def materialize_release(values_dir: Path) -> dict:
    helmfile = yaml.safe_load((values_dir / "helmfile.yaml").read_text())
    for release in helmfile.get("releases", []):
        if str(release.get("chart", "")).endswith("/materializationengine"):
            return release
    fail(f"no materializationengine release in {values_dir / 'helmfile.yaml'}")


def values_files(values_dir: Path, release: dict) -> list[Path]:
    files = []
    for entry in release.get("values", []):
        if not isinstance(entry, str):
            fail(f"inline values in helmfile.yaml are not supported: {entry!r}")
        path = values_dir / entry
        # helmfile treats a missing file in the list as an optional override.
        if path.is_file():
            files.append(path)
        else:
            print(f"render.py: skip missing values file {entry}", file=sys.stderr)
    return files


def merged_cloudsql(files: list[Path]) -> dict:
    """The cloudsql values, last file wins, as helm merges them."""
    cloudsql: dict = {}
    for path in files:
        data = yaml.safe_load(path.read_text()) or {}
        cloudsql.update(data.get("cloudsql") or {})
    return cloudsql


def helm_template(chart: Path, files: list[Path]) -> list[dict]:
    cmd = ["helm", "template", "materialization-engine", str(chart)]
    for path in files:
        cmd += ["-f", str(path)]
    cmd += [
        "--set-string",
        f"cloudsql.username={USER_PLACEHOLDER}",
        "--set-string",
        f"cloudsql.password={PASSWORD_PLACEHOLDER}",
        "--show-only",
        "templates/configmap.yaml",
        "--show-only",
        "templates/ray_job_template_configmap.yaml",
    ]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        fail(f"helm template failed:\n{result.stderr}")
    return [doc for doc in yaml.safe_load_all(result.stdout) if doc]


def config_map(docs: list[dict], name: str) -> dict:
    for doc in docs:
        if doc.get("kind") == "ConfigMap" and doc["metadata"]["name"] == name:
            return doc["data"]
    fail(f"helm output has no ConfigMap {name}. Is ray.enabled true in the values?")


def render_config(data: dict) -> str:
    config = data["config.cfg"]
    uri_lines = [line for line in config.splitlines() if "SQLALCHEMY_DATABASE_URI" in line]
    if len(uri_lines) != 1 or USER_PLACEHOLDER not in uri_lines[0] or PASSWORD_PLACEHOLDER not in uri_lines[0]:
        fail("config.cfg has no single SQLALCHEMY_DATABASE_URI line with both placeholders")
    if config.count(PASSWORD_PLACEHOLDER) != 1:
        fail("the password placeholder is in config.cfg more than once")
    return config.rstrip("\n") + "\n" + OVERRIDE_BLOCK


def head_spec(ray_data: dict) -> dict:
    template = yaml.safe_load(ray_data["rayjob-template.yaml"])
    return template["spec"]["rayClusterSpec"]["headGroupSpec"]["template"]["spec"]


def named(items: list[dict], name: str) -> dict:
    for item in items:
        if item.get("name") == name:
            return item
    fail(f"no container {name} in the ray head template")


def env_lines(env: list[dict], overrides: dict[str, str]) -> str:
    lines = []
    for item in env:
        name = item["name"]
        if "valueFrom" in item:
            fail(f"env {name} is a valueFrom reference. Only literal values can be copied.")
        if name == "RAY_ENABLED":
            fail("the head env sets RAY_ENABLED. Locally it must stay unset (init_upload_state).")
        value = overrides.get(name, str(item.get("value", "")))
        if "\n" in value or "'" in value:
            fail(f"env {name} has a newline or a single quote, which env files cannot hold")
        # Single quotes: docker compose reads the value literally.
        lines.append(f"{name}='{value}'")
    return "\n".join(lines) + "\n"


def resolve_tfstate_ref(ref: str) -> str:
    """Resolve ref+tfstategs://BUCKET/PATH/output.NAME, as vals would.

    The state goes from gcloud to this process through a pipe and is never
    written or printed. Only a non-sensitive output is returned.
    """
    match = re.fullmatch(r"ref\+tfstategs://([^/]+)/(.+)/output\.([A-Za-z0-9_]+)", ref)
    if not match:
        fail(f"unsupported reference: {ref}")
    bucket, state_path, output = match.groups()
    result = subprocess.run(
        ["gcloud", "storage", "cat", f"gs://{bucket}/{state_path}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        fail(f"gcloud could not read the terraform state:\n{result.stderr}")
    try:
        state = json.loads(result.stdout)
    except json.JSONDecodeError:
        fail("the terraform state is not JSON")
    entry = state.get("outputs", {}).get(output)
    if entry is None:
        fail(f"the terraform state has no output {output}")
    if entry.get("sensitive"):
        fail(f"the terraform output {output} is sensitive. Not used.")
    return str(entry["value"])


def proxy_instance(proxy: dict) -> str:
    args = list(proxy.get("args", []))
    flags = [arg for arg in args if arg.startswith("--")]
    positional = [arg for arg in args if not arg.startswith("--")]
    if flags != EXPECTED_PROXY_FLAGS or len(positional) != 1:
        fail(
            "the cloudsql-proxy args of the chart changed. Update compose.yaml and "
            f"EXPECTED_PROXY_FLAGS in render.py. Rendered args: {args}"
        )
    instance = positional[0]
    # project:region:name, where name can be a terraform state reference.
    project, region, name = instance.split(":", 2)
    if name.startswith("ref+"):
        name = resolve_tfstate_ref(name)
    if "ref+" in project or "ref+" in region:
        fail(f"unresolved reference in the proxy instance: {instance}")
    return f"{project}:{region}:{name}"


def db_secret(cloudsql: dict) -> tuple[str, str]:
    """(project, name) of the Secret Manager secret that holds the DB credentials."""
    pattern = r"ref\+gcpsecrets://([^/#]+)/([^/#]+)#(username|password)"
    found = {}
    for key in ("username", "password"):
        match = re.fullmatch(pattern, str(cloudsql.get(key, "")))
        if not match or match.group(3) != key:
            fail(f"cloudsql.{key} is not a ref+gcpsecrets://<project>/<name>#{key} pointer")
        found[key] = match.group(1, 2)
    if found["username"] != found["password"]:
        fail("cloudsql.username and cloudsql.password point to different secrets")
    return found["password"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--values-dir", required=True, type=Path)
    parser.add_argument("--env-name", required=True, help="name of the environment, for example ltv")
    parser.add_argument("--chart", default=DEFAULT_CHART, type=Path)
    parser.add_argument("--out", default=DEFAULT_OUT, type=Path)
    args = parser.parse_args()

    values_dir = args.values_dir.resolve()
    out = args.out.resolve()
    out.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(out, 0o700)
    require_gitignored(out)

    release = materialize_release(values_dir)
    chart_version = yaml.safe_load((args.chart / "Chart.yaml").read_text())["version"]
    if str(release.get("version")) != str(chart_version):
        print(
            f"render.py: WARNING: the helmfile pins chart {release.get('version')}, "
            f"but the local chart is {chart_version}",
            file=sys.stderr,
        )

    files = values_files(values_dir, release)
    docs = helm_template(args.chart, files)

    config = render_config(config_map(docs, CONFIG_MAP))

    spec = head_spec(config_map(docs, RAY_CONFIG_MAP))
    head = named(spec["containers"], "ray-head")
    head_env = env_lines(head["env"], {"REDIS_HOST": "redis", "REDIS_SERVICE_HOST": "redis"})
    proxy = named(spec.get("initContainers", []), "cloudsql-proxy")
    proxy_env = env_lines(proxy.get("env", []), {})

    instance = proxy_instance(proxy)
    secret_project, secret_name = db_secret(merged_cloudsql(files))
    infra_env = "\n".join(
        [
            f"MAT_ENV={args.env_name}",
            f"MAT_SQL_INSTANCE={instance}",
            f"MAT_DB_SECRET_PROJECT={secret_project}",
            f"MAT_DB_SECRET={secret_name}",
        ]
    ) + "\n"

    write_private(out / "config.cfg", config)
    write_private(out / "head.env", head_env)
    write_private(out / "proxy.env", proxy_env)
    write_private(out / "infra.env", infra_env)
    print(f"render.py: rendered {args.env_name} (chart {chart_version}) to {out}")


if __name__ == "__main__":
    main()
