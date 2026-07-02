"""This script erases a database and imports from a dump"""

from pathlib import Path
import json
from arango import ArangoClient, database

def import_from_dump(db : database.StandardDatabase, dump_path : str):
    """
    Imports a whole database JSON dump from a path to the parent folder each collection will have the same name
    as the file it comes from. Edge collections are detected automaticaly. If a collection with the same name, is already
    in use inside a graph the function will fail because it can't delete it.

    :param db: The ArangoDB database API wrapper of the target database
    :type db: arango.database.StandardDatabase
    :param dump_path: The path to the folder containing the dump, as a string
    :type dump_path: str
    """
    if not Path(dump_path).exists():
        raise FileNotFoundError


    json_list = Path(dump_path).glob('*.json')

    try:
        current_json = next(json_list)
    except StopIteration:
        raise FileNotFoundError

    while current_json is not None:
        collection_name : str = current_json.name.split(".json")[0]

        if db.has_collection(collection_name):
            db.delete_collection(collection_name)

        with open(current_json) as f:
            data: dict = json.load(f)

            if "_from" in data[0]: # we are handling an edge list
                collection : database.StandardCollection = db.create_collection(collection_name, edge=True)
            else: #It's a document collection
                collection : database.StandardCollection = db.create_collection(collection_name)

            collection.insert_many(data, raise_on_document_error=True)

        try:
            current_json = next(json_list)
        except StopIteration:
            break


def import_from_dump_main(host: str, db_name: str, user: str, password: str, dump_path: str):
    client: ArangoClient = ArangoClient(hosts=host)
    db: database.StandardDatabase = client.db(db_name, username=user,
                                                  password=password)

    import_from_dump(db, dump_path)

if __name__ == "__main__":

    testclient: ArangoClient = ArangoClient(hosts="http://localhost:8529")
    testdb: database.StandardDatabase = testclient.db("TEATIME", username="root",
                                              password="test")

    import_from_dump(testdb, "data/DumpArango")
