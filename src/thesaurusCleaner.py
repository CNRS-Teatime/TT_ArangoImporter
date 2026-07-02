"""
Cleanup procedure for our thesaurus collections
It will check for invalid relations and properties, to reduce friction in the use of the data
"""

import threading
from arango import database, exceptions, ArangoClient

def test_edges(db, edges, results):
    for edge in edges:
        try:
            _to = db.document(edge['_to'])
            _from = db.document(edge['_from'])
            if _to is None or _from is None:
                results.append(edge)

        except (exceptions.DocumentGetError, exceptions.DocumentRevisionError) as e:
            results.append(edge)

def cleanup_edge_collection(db: database.StandardDatabase, collection_name: str):
    """
    Deletes invalid edges in the desired collection.

    :param db: An pyArango database API wrapper
    :type db: arango.database.StandardDatabase
    :param collection_name: The name of the collection in which to perform the cleanup
    :type collection_name: str
    """
    to_delete = []
    threads = []

    if not db.has_collection(collection_name):
        print(f"Collection {collection_name} does not exist")
    else:
        if db.collection(collection_name).properties()['edge']:
            print(f"Fetching {collection_name}...")
            #Now we want to test every document in the edges to see if they exist
            #It feels very trashy tho
            all_doc = db.collection(collection_name).all()
            all_list = [_ for _ in all_doc]
            nb_edges = len(all_list)
            print(f"Now checking {collection_name}...")
            if nb_edges < 500:
                for edge in all_list:
                    try:
                        _to = db.document(edge['_to'])
                        _from = db.document(edge['_from'])
                        if _to is None or _from is None:
                            to_delete.append(edge)

                    except (exceptions.DocumentGetError, exceptions.DocumentRevisionError) as e:
                        to_delete.append(edge)
            else:
                i = 0
                while i < nb_edges:
                    i += 500
                    if i >= nb_edges:
                        i = nb_edges

                    t = threading.Thread(target=test_edges, args=(db, all_list[i-500:i], to_delete))
                    threads.append(t)

            for t in threads:
                t.start()

            for t in threads:
                t.join()
        else:
            print(f"{collection_name} is not an edge collection, cannot perform this type of cleanup")

        print(f"Deleting for {collection_name} now...")

        db.collection(collection_name).delete_many(to_delete)


def cleanup_database(host: str, db_name: str, user_name: str, password: str):
    """
    Uses multi-threading to perform cleanup on non-system, edge collections.
    The cleanup will remove any edge containing invalid target or origin.

    :param host: hostname of the arangoDB instance
    :type host: str
    :param db_name: name of the database in which to perform cleanup
    :type db_name: str
    :param user_name: Usename for credentials
    :type user_name: str
    :param password: Password for credentials
    :type password: str
    """
    client: ArangoClient = ArangoClient(hosts=host)
    db: database.StandardDatabase = client.db(db_name, username=user_name,
                                              password=password)

    collections = db.collections()

    threads = []

    for coll in collections:
        if not coll['system']:
            if db.collection(coll['name']).properties()['edge']:
                t = threading.Thread(target=cleanup_edge_collection, args=(db, coll['name']))
                threads.append(t)

    for t in threads:
        t.start()

    for t in threads:
        t.join()

if __name__ == "__main__":
    testclient = ArangoClient("http://localhost:8529")

    testdatabase = testclient.db("TEATIME", "root", "test")

    cleanup_edge_collection(testdatabase, "intraTheso_relations")
