
import json
from arango import ArangoClient, database, Response

if __name__ == "__main__":
    NAME = "aioli_objects"

    entries: list = []
    edges: list = []
    with open("data/aioli-graph.json") as file:
        data : dict = json.load(file)
        for d in data[0]["nodes"]:
            entries.append(d["data"])

        for e in data[0]['links']:
            edges.append(e['data'])

    client: ArangoClient = ArangoClient(hosts="http://localhost:8529")
    db: database.StandardDatabase = client.db("TEATIME", username="root",
                                                   password="test")

    if db.has_collection(NAME):
        db.delete_collection(NAME)

    if db.has_collection(NAME + "_EDGES"):
        db.delete_collection(NAME + "_EDGES")

    nodes_colletion = db.create_collection(NAME)
    edges_collection = db.create_collection(NAME + "_EDGES", edge=True)

    nodes_colletion.insert_many(entries)

    """edges_to_remove = []

    for edge in edges:
        if edge['nature'] == "owns" or edge['nature'] == "isSharedWith":
            edges_to_remove.append(edge)

    for edge in edges_to_remove:
        edges.remove(edge)"""

    edges_collection.insert_many(edges)