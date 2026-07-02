
import sys, os
from thesaurusCreator import get_config
from arango import ArangoClient, database, graph

def create_graph(db : database.StandardDatabase, graph_list : list[dict]) -> None:
    """
    Creates the desired graph from a JSON configuration file stored as a dict.
    WILL OVERWRITE DATA IF THE GRAPH NAME ALREADY EXISTS

    :param db: The database in which to create the graph
    :type db: arango.database.StandardDatabase
    :param graph_list: a list of dictionaries containing graph definitions
    :type graph_list: list[dict] each dict contains these keys : name, relations. They are defined in the readme as the graph configuration JSON
    """
    for g in graph_list:
        if db.has_graph(g["name"]):
            db.delete_graph(g["name"])

        curr_graph = db.create_graph(g["name"])

        #Creating the edge definitions
        for definition in g["relations"]:
            curr_graph.create_edge_definition(
                edge_collection = definition["edge_collection"],
                from_vertex_collections = definition["from_vertex_collections"],
                to_vertex_collections = definition["to_vertex_collections"]
            )
        print(f"Created graph {g["name"]}")

def create_graph_from_config(config_path : str):
    """
    This function fetches the configuration file, verifies it against the schema and correctly calls the sister function create_graph()

    :param config_path: The path to the configuration file
    :type config_path: str
    """
    config: dict = get_config(config_path, "config/graph-config-schema.json")
    graphs: list = config["graphs"]

    client: ArangoClient = ArangoClient(hosts=os.getenv("DB_ADDRESS"))
    curr_db: database.StandardDatabase = client.db(name=os.getenv("DB_NAME"), username=os.getenv("DB_USER"),
                                                   password=os.getenv("DB_PASSWORD"))

    create_graph(curr_db, graphs)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Please provide config file path as first argument")
        sys.exit()

    create_graph_from_config(sys.argv[1])
