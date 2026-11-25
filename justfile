set quiet
set positional-arguments

# The deployment to copy: ltv (default, not production) or minnie.
env := "ltv"
datastack := "minnie65_phase3_v1"

# Only the folder name is here. render.py reads the rest from the private submodule.
values_dir := if env == "ltv" { "ltv/ltv7" } else if env == "minnie" { "minnie/minniev7" } else { error("unknown env " + env + ": use ltv or minnie") }

mat_dir := "local/materialize"
mat_rendered := mat_dir / ".rendered"
compose := "docker compose -f " + mat_dir / "compose.yaml" + " --env-file " + mat_rendered / "infra.env"

# Bash lines for the shebang recipes. They read the rendered infrastructure names.
_mat_infra := '''
if [ ! -f local/materialize/.rendered/infra.env ]; then
  echo "error: run 'just mat-render' first" >&2; exit 1
fi
set -a; source local/materialize/.rendered/infra.env; set +a
# The export container bind-mounts this folder, so it must exist.
mkdir -p local/materialize/exports
'''

# Gets the DB credentials into this shell only. The values never go to argv or
# the terminal. `docker compose run -e NAME` copies them by name.
# Source: local/materialize/db-credentials.env if it has a password (workaround),
# else Secret Manager.
_mat_creds := '''
_mat_creds_file=local/materialize/db-credentials.env
_mat_field() { python3 -I -c 'import sys; k = sys.argv[2] + "="; v = [l.rstrip("\r\n")[len(k):] for l in open(sys.argv[1]) if l.startswith(k)]; sys.stdout.write(v[-1] if v else "")' "$_mat_creds_file" "$1"; }
if [ -f "$_mat_creds_file" ] && [ -n "$(_mat_field MAT_DB_PASSWORD)" ]; then
  if ! git check-ignore -q "$_mat_creds_file"; then
    echo "error: git does not ignore $_mat_creds_file" >&2; exit 1
  fi
  chmod 600 "$_mat_creds_file"
  if [ "$(_mat_field MAT_DB_ENV)" != "$MAT_ENV" ]; then
    echo "error: $_mat_creds_file is for '$(_mat_field MAT_DB_ENV)', but .rendered is for '$MAT_ENV'" >&2; exit 1
  fi
  echo "using DB credentials from $_mat_creds_file ($MAT_ENV)" >&2
  MAT_DB_USER="$(_mat_field MAT_DB_USER)"
  MAT_DB_PASSWORD="$(_mat_field MAT_DB_PASSWORD)"
else
  _mat_secret="$(gcloud secrets versions access latest --secret="$MAT_DB_SECRET" --project="$MAT_DB_SECRET_PROJECT")"
  MAT_DB_USER="$(printf '%s' "$_mat_secret" | python3 -I -c 'import json,sys; sys.stdout.write(json.load(sys.stdin)["username"])')"
  MAT_DB_PASSWORD="$(printf '%s' "$_mat_secret" | python3 -I -c 'import json,sys; sys.stdout.write(json.load(sys.stdin)["password"])')"
  unset _mat_secret
fi
if [ -z "$MAT_DB_USER" ] || [ -z "$MAT_DB_PASSWORD" ]; then
  echo "error: the DB secret has no username or password" >&2; exit 1
fi
PGUSER="$MAT_DB_USER"; PGPASSWORD="$MAT_DB_PASSWORD"
export MAT_DB_USER MAT_DB_PASSWORD PGUSER PGPASSWORD
'''

# Build the materializationengine image from the submodule (native architecture, never pushed).
mat-build:
    docker build -t materializationengine:dev submodules/MaterializationEngine

# Render config.cfg and the head pod env for `env` into local/materialize/.rendered/.
mat-render:
    uv run --no-project --with pyyaml python -I {{ mat_dir }}/render.py --values-dir submodules/terraform-cave-private/{{ values_dir }}/helmfile --env-name {{ env }}

# Start the Cloud SQL proxy and Redis, then wait until the DB answers.
mat-up:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ _mat_infra }}
    if [ "$MAT_ENV" != "{{ env }}" ]; then
      echo "error: .rendered is for $MAT_ENV. Run 'just env={{ env }} mat-render' first." >&2; exit 1
    fi
    {{ compose }} up -d cloudsql-proxy redis
    for _ in $(seq 60); do
      if {{ compose }} run --rm --no-deps -T export pg_isready -q -h 127.0.0.1 -p 3306; then
        echo "DB proxy for $MAT_ENV is ready"; exit 0
      fi
      sleep 2
    done
    echo "error: the DB proxy did not become ready. See: {{ compose }} logs cloudsql-proxy" >&2
    exit 1

# Stop all services and delete the Redis data and Ray spill volumes.
mat-down:
    {{ compose }} --profile tools --profile web down --volumes --remove-orphans

# Run the production Ray entrypoint for one table and version. Deletes the old local output first.
# `specs` is an optional JSON list of output specs. Without it, the export finds the default specs.
mat-export table version specs="":
    #!/usr/bin/env bash
    set -euo pipefail
    {{ _mat_infra }}
    table={{ quote(table) }}
    version={{ quote(version) }}
    specs={{ quote(specs) }}
    if ! [[ "$table" =~ ^[A-Za-z0-9_]+$ ]] || ! [[ "$version" =~ ^[0-9]+$ ]]; then
      echo "error: the table must be an identifier and the version a number" >&2; exit 1
    fi
    specs_args=()
    if [ -n "$specs" ]; then
      if ! printf '%s' "$specs" | python3 -I -c 'import json,sys; s = json.load(sys.stdin); sys.exit(0 if isinstance(s, list) else 1)'; then
        echo "error: specs must be a JSON list of output specs" >&2; exit 1
      fi
      specs_args=(--output-specs "$specs")
    fi
    mkdir -p {{ mat_dir }}/exports
    if ! git check-ignore -q {{ mat_dir }}/exports; then
      echo "error: git does not ignore {{ mat_dir }}/exports" >&2; exit 1
    fi
    exports="$(cd {{ mat_dir }}/exports && pwd -P)"
    target="$(python3 -I -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$exports/{{ datastack }}/v$version/$table")"
    case "$target" in
      "$exports"/?*/v?*/?*) rm -rf -- "$target" ;;
      *) echo "error: $target is not under $exports" >&2; exit 1 ;;
    esac
    {{ _mat_creds }}
    {{ compose }} run --rm -e MAT_DB_USER -e MAT_DB_PASSWORD export \
      python -m materializationengine.rayjobs.entrypoints.deltalake_export \
      --datastack {{ datastack }} --version "$version" --table "$table" \
      --job-id "local-$(date +%Y%m%d-%H%M%S)" ${specs_args[@]+"${specs_args[@]}"}

# Run the web app with login off, for the Delta Lake wizard at https://localhost:8080/materialize/deltalake/.
mat-web:
    #!/usr/bin/env bash
    set -euo pipefail
    # Ctrl-C stops it. The certificate is self-signed. Anyone on this machine can use
    # the app while it runs, and the DB stays read-only. Submit only queues a Celery
    # task in the local Redis, and no worker runs it: run the specs that step 3
    # shows with `just mat-export`.
    {{ _mat_infra }}
    {{ _mat_creds }}
    {{ compose }} --profile web up -d web-port
    trap '{{ compose }} --profile web stop web-port >/dev/null 2>&1 || true' EXIT
    echo "wizard: https://localhost:8080/materialize/deltalake/" >&2
    {{ compose }} run --rm -e MAT_DB_USER -e MAT_DB_PASSWORD \
      -e AUTH_DISABLED=true -e FLASK_RUN_PORT=8080 export python run.py

# Run any command in the export container with the DB credentials, e.g. `just mat-run bash`.
mat-run +cmd:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ _mat_infra }}
    {{ _mat_creds }}
    {{ compose }} run --rm -e MAT_DB_USER -e MAT_DB_PASSWORD -e PGUSER -e PGPASSWORD export "$@"

# Fail if a staged file has a secret pointer or an infrastructure name. Run before each commit.
mat-audit:
    #!/usr/bin/env bash
    set -euo pipefail
    mapfile -t files < <(git diff --cached --name-only --diff-filter=ACMR)
    if [ "${#files[@]}" -eq 0 ]; then echo "mat-audit: nothing staged"; exit 0; fi
    status=0
    # Generic markers. The tooling files describe these patterns, so they are skipped here only.
    generic=(-e 'ref[+]' -e 'gcp[s]ecrets' -e 'tfstate[g]s' -e '[.]iam[.]gserviceaccount[.]com' -e 'private[_]key' -e '-postgres[-]credentials' -e 'terraform-remote-[b]ackend')
    if git grep --cached -n -I -E "${generic[@]}" -- "${files[@]}" \
        ':(exclude)justfile' ':(exclude){{ mat_dir }}/render.py'; then
      status=1
    fi
    # Names that render.py found. These are checked in every staged file.
    if [ -f {{ mat_rendered }}/infra.env ]; then
      set -a; source {{ mat_rendered }}/infra.env; set +a
      names=(-e "$MAT_SQL_INSTANCE" -e "${MAT_SQL_INSTANCE##*:}" -e "$MAT_DB_SECRET")
      if git grep --cached -n -I -F "${names[@]}" -- "${files[@]}"; then status=1; fi
    else
      echo "mat-audit: warning: no {{ mat_rendered }}/infra.env, so infrastructure names are not checked" >&2
    fi
    # The hard-coded password, if any. It goes to git grep through a pipe, not argv.
    creds={{ mat_dir }}/db-credentials.env
    if [ -f "$creds" ]; then
      if ! git check-ignore -q "$creds"; then echo "mat-audit: git does not ignore $creds" >&2; status=1; fi
      if git ls-files --cached --error-unmatch "$creds" >/dev/null 2>&1; then echo "mat-audit: $creds is in the index" >&2; status=1; fi
      if python3 -I -c 'import sys; v = [l.rstrip("\r\n")[16:] for l in open(sys.argv[1]) if l.startswith("MAT_DB_PASSWORD=")]; sys.exit(0 if v and v[-1] else 1)' "$creds"; then
        if git grep --cached -q -I -F -f <(python3 -I -c 'import sys; v = [l.rstrip("\r\n")[16:] for l in open(sys.argv[1]) if l.startswith("MAT_DB_PASSWORD=")]; print(v[-1])' "$creds") -- "${files[@]}"; then
          echo "mat-audit: a staged file contains the DB password (file names not shown here)" >&2; status=1
        fi
      fi
    fi
    if [ "$status" -ne 0 ]; then echo "mat-audit: FAILED, see the matches above" >&2; exit 1; fi
    echo "mat-audit: ok (${#files[@]} staged files)"
