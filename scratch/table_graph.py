# %%

import matplotlib.pyplot as plt
import networkx as nx
from caveclient import CAVEclient

client = CAVEclient("minnie65_phase3_v1", version=1718)

# %%
client.materialize.get_table_metadata("synapses_pni_2")

# %%
# table_names = client.materialize.get_tables()
metadatas = client.materialize.get_tables_metadata()

# %%


g = nx.DiGraph()
for metadata in metadatas:
    table = metadata["table_name"]
    g.add_node(table)

    if metadata["reference_table"] is not None:
        g.add_edge(table, metadata["reference_table"])

# %%
# remove all components that consist only of a single node

for component in list(nx.weakly_connected_components(g)):
    if len(component) == 1:
        g.remove_node(next(iter(component)))

# %%



pos = nx.spring_layout(g)


plt.figure(figsize=(12, 12))
nx.draw(g, pos, with_labels=True, node_size=200, node_color="lightblue", font_size=10)
plt.title("Table Dependency Graph")
plt.show()


#%%

for component in nx.weakly_connected_components(g):
    sub_g = g.subgraph(component)
    pos = nx.spring_layout(sub_g)


    plt.figure(figsize=(12, 12))
    nx.draw(sub_g, pos, with_labels=True, node_size=200, node_color="lightblue", font_size=10)
    plt.title("Table Dependency Graph")
    plt.show()
