"""
This package will read every thesaurus edges contained inside the database and return a csv with the names and counts (per thesaurus)
"""

from arango import ArangoClient, database

# AQL does not let us dynamicaly iterate over collections when querying so we need to get the collections name and iterate on the client
def get_all_edge_col_names(db: database.StandardDatabase) -> list:
    """
    Queries for all the collection name ending in _relations in the specified database. This is done to only get
    edge collections of thesauri we inserted with the thesaurusCreator tool.
    :param db: The arango API wrapper for the desired database
    :type db: Arango.database.StandardDatabase:
    :return: A list of strings containing the names
    """
    cursor = db.aql.execute(
        "FOR c IN COLLECTIONS() \
            FILTER LIKE(c.name, 'th%_relations') \
            RETURN c.name")
    return [_ for _ in cursor]


def count_labels(db: database.StandardDatabase, col : str) -> dict:
    """
    Count the occurences of each types in a given edge collections
    :param db: The arango API wrapper for the desired database
    :type db: Arango.database.StandardDatabase
    :param col: The name of the collection for wich we want to count types
    :type col: str
    :returns: A dictionary, with type names as keys and number of occurences as values
    """
    cursor = db.aql.execute(
        "FOR doc IN @@name\
         RETURN doc.`type`",
         bind_vars={'@name': col})
    counting_dictionary : dict = {}
    for label in cursor:
        if label in counting_dictionary:
            counting_dictionary[label] += 1
        else:
            counting_dictionary[label] = 1
    return counting_dictionary

if __name__ == "__main__":
    client : ArangoClient = ArangoClient("http://localhost:8529")

    currentdb : database.StandardDatabase = client.db("TEATIME", "root", password="test")
    colnames : list = get_all_edge_col_names(currentdb)
    
    results : dict = {}
    for name in colnames :
        countedLabels : dict = count_labels(currentdb, name)
        results[name] = countedLabels

    with open("results.csv", 'w') as f:
        for name in results:
            for res in results[name]:
                f.write(name + ',' + res + ',' + str(results[name][res]) + '\r')