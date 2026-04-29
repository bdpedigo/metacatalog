# %%

from caveclient import CAVEclient

client = CAVEclient("minnie65_phase3_v1")

client.materialize.tables

# %%

dir(client.materialize.tables.synapses_pni_2)

# %%
client.materialize.tables.synapses_pni_2.fields
# %%
client.materialize.get_view_schema("aibs_cell_info")

# %%
dir(client.materialize.tables.synapses_pni_2)

# %%
client.materialize.tables.synapses_pni_2.numeric_fields

# %%
client.materialize.views.aibs_cell_info.fields

# %%
fields = client.materialize.tables["synapses_pni_2"].fields
fields = [name if not name.endswith("_bbox") else name[:-5] for name in fields]
fields
