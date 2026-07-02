""" 
Create two new collections from an opentheso database graph
The scripts takes a JSON config file in entry
"""
import json, requests, os
from arango import ArangoClient, database
from jsonschema import validate, ValidationError


def get_config(config_path: str, schema_path: str = None) -> dict:
    """
    Parse the configuration file and validate it against the JSON schema.

    :param config_path: A path to the JSON configuration file
    :type config_path: str

    :param schema_path: A path to the JSON schema (optional)
    :type schema_path: str

    :return: A dictionary containing the validated configuration JSON
    """
    with open(config_path) as file:
        config_list = json.load(file)

        if schema_path is None:
            return config_list
        # If we've got a schema we validate against it
        with open(schema_path) as schemafile:
            schema = json.load(schemafile)
            try :
                validate(config_list, schema)
            except ValidationError:
                print("YOUR CONFIG FILE IS INVALID")
                raise 
            return config_list

def get_collections(db : database.StandardDatabase, name: str) -> tuple[database.StandardCollection, database.StandardCollection] :
    """
    Create or truncate the collections with name `name` and `name_relation` and returns the standard API wrapper for ArangoDB collections
    :param db: The arangoDB database wrapper
    :type db: database.StandardDatabase
    :param name: The chosen collection name
    :type name: str
    :returns: A tuple with the document collection and edge collection fetched.
    """

    if db.has_collection(name):
        nodes_collection : database.StandardCollection = db.collection(name)
        nodes_collection.truncate()
    else:
        nodes_collection : database.StandardCollection = db.create_collection(name)

    if db.has_collection(name + "_relations"):
        edges_collection : database.StandardCollection = db.collection(name + "_relations")
        edges_collection.truncate()
    else:
        edges_collection : database.StandardCollection = db.create_collection(name + "_relations", edge=True)

    return nodes_collection, edges_collection

def insert_graph_thesaurus(db : database.StandardDatabase, thesaurus_config : dict, thesaurus : dict):
    """
    Insert a thesaurus into a designated Arango Database using its configuration and JSON. If the insertion is unsuccesful, the tuple will contain two empty lists.

    :param db: The arango database API wrapper
    :type db: arango.database.StandardDatabase
    :param thesaurus_config: (part of) the JSON config for the desired thesaurus, containing its name and source
    :type thesaurus_config: dict
    :param thesaurus: The full JSON of the desired thesaurus, with an entry for each node and edge.
    :type thesaurus: dict

    :return: The list of skipped edges, and the list of added edges, in this order.
    """
    skipped_edges = []

    # Chekc if collection already exists we delete it
    nodes_collection, edges_collection = get_collections(db, thesaurus_config['name'])

    nodes_collection.truncate()
    edges_collection.truncate()

    print("Processing nodes...")

    new_nodes = nodes_collection.insert_many(thesaurus['nodes'], return_new=True)

    print("Processing edges...")

    skip = 0

    for edge in thesaurus['relationships']:

        start = next((item for item in new_nodes if item['new']['id'] == edge["start"]), False) # Searching for node wich original id was the edge start
        to = next((item for item in new_nodes if item['new']['id'] == edge["end"]), False)

        if start and to:
            edge["_from"] = start['_id']
            del edge["start"]

            edge["_to"] = to['_id']
            del edge["end"]

        else:
            skip += 1
            skipped_edges.append(edge)
            del edge

    print(f"Skipped {skip} edges out of {len(thesaurus['relationships'])}")

    result = edges_collection.insert_many(thesaurus['relationships'], silent=True, raise_on_document_error=True)

    if result:
        print(f"Succesfully imported thesaurus {thesaurus_config['name']}")
        return skipped_edges, new_nodes

    return [], [] #Import was unsuccessful so we return nothing

def fetch_thesaurus(thesori_config_list: dict) -> list:
    """  
    Goes through the list of thesaurus configuration and fetches each one individually via a REST GET request
    :param thesori_config_list: a dictionnary containing all the thesaurus config, the schema is in config/theso-config-schema.json
    :type thesori_config_list: dict
    :returns: A list of the fetched thesaurus, each one being a dict parsed with the JSON library.
    """
    theso_list : list = []
    for thesaurus in thesori_config_list:
        api_url : str = thesaurus["source"]
        print(f"Requesting thesaurus {api_url} ...")
        response : requests.models.Response  = requests.get(api_url, {"login" : "marwan.russier", "password" : "Rydxos-xifnyz-bocte7"})
        if response.status_code == 200:
            theso_list.append(response.json())
            print(f"Thesaurus {thesaurus['source']} succesfully fetched from remote")
        else :
            theso_list.append(None)
            print(f"Error fetching thesaurus {thesaurus['source']}")
    return theso_list

def generate_inter_thesauri_edges(db : database.StandardDatabase, all_nodes : list, edges : list) -> list:
    """
    Here we take into account the inter-thesauri edges, the objective is to be able to create a "master" graph that links all thesaurus graphs
    increasing exhaustivity and interconnection. The edges are put in their own separate Shared_EDGES collection. This is the only edges collection
    that is not exclusively linking nodes from a single NODES collection.

    :param db: The arango database API wrapper
    :type db: arango.database.StandardDatabase
    :param all_nodes: A list of all nodes that exists in the database, this is necessary to get the internal ArangoDB IDs
    :type all_nodes: list
    :param edges: A list of all the edges we need to create
    :type edges: list
    """
    i = 0
    length = len(edges)
    while i < length:
        if not edges[i]:
            del edges[i]
            break

        start : dict = {}
        to : dict = {}
        for item in all_nodes:
            if item['new']['id'] == edges[i]['start']:
                start = item
            if item['new']['id'] == edges[i]['end']:
                to = item

        if start != {} and to != {}:
            edges[i]["_from"] = start['_id']
            del edges[i]["start"]
            
            edges[i]["_to"] = to['_id']
            del edges[i]["end"]
        else:
            del edges[i]
            length -= 1
            i -= 1

        i += 1

    # Check if collection already exists
    # Otherwise we create it
    if db.has_collection("Shared_EDGES"):
        db.delete_collection("Shared_EDGES")

    edges_collection : database.StandardCollection = db.create_collection("Shared_EDGES", edge=True)

    print("Inserted Shared_EDGES")
    return edges_collection.insert_many(edges, return_new=True)

# These functions work on the raw import, which is much more detailed

def create_thesaurus_dict(parsed_thesaurus : dict) -> list:
    """
        Creates an arangoDB formated list of thesaurus entry, from the raw thesaurus fetched from openTheso. We use the URI's of each type of entry to figure out
        where the interesting data is in the raw thesaurus.

        :param parsed_thesaurus: Raw thesaurus, fetched from opentheso and parsed into a dict by the JSON library
        :type parsed_thesaurus: dict
        :returns: The list of documents created, that needs to be inserted into the ArangoDB collection. Each document being a thesaurus entry stored as a dict
    """
    thesaurus : list = []

    for entry in parsed_thesaurus:
        # Here we prepare the schema for each annotation
        # Comments next to key value pairs are the URI's associated with them in the original data
        annotation: dict = {
            "_key": entry.split("/")[-1],  # The id is the last element of the URI separated by /
            "labels": [],  # http://www.w3.org/2004/02/skos/core#prefLabel Remove the type from this one
            "type": None,  # http://www.w3.org/1999/02/22-rdf-syntax-ns#type
            "created": None,  # http://purl.org/dc/terms/created
            "modified": None,  # http://purl.org/dc/terms/modified
            "description": None,  # http://purl.org/dc/terms/description Remove the type
            "ark": entry,  # The key value of the entry
            "name": None,  # The first label value
            "note": None,  # "http://www.w3.org/2004/02/skos/core#scopeNote"
            "definition": None,  # http://www.w3.org/2004/02/skos/core#definition
        }

        # The data being semi-structured we have to check if the key exists before doing anything with it

        if "http://www.w3.org/2004/02/skos/core#prefLabel" in parsed_thesaurus[entry]:
            annotation["labels"] = parsed_thesaurus[entry]["http://www.w3.org/2004/02/skos/core#prefLabel"]
        for label in annotation["labels"]:
            del label["type"]

            # We do not have a name without a label so we define it here
            annotation["name"] = annotation["labels"][0]["value"]

        if "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" in parsed_thesaurus[entry]:
            try:  # We only want the skos types
                annotation["type"] = parsed_thesaurus[entry]["http://www.w3.org/1999/02/22-rdf-syntax-ns#type"][0]["value"].split("#")[1]
                pass
            except IndexError:  # Otherwise we skip the entry
                print(parsed_thesaurus[entry]["http://www.w3.org/1999/02/22-rdf-syntax-ns#type"][0]["value"])
                continue

        if annotation["type"] != "Concept":  # We only want to get concepts
            continue

        if "http://purl.org/dc/terms/created" in parsed_thesaurus[entry]:
            annotation["created"] = parsed_thesaurus[entry]["http://purl.org/dc/terms/created"][0]["value"]

        if "http://purl.org/dc/terms/modified" in parsed_thesaurus[entry]:
            annotation["modified"] = parsed_thesaurus[entry]["http://purl.org/dc/terms/modified"][0]["value"]

        if "http://purl.org/dc/terms/description" in parsed_thesaurus[entry]:
            annotation["description"] = parsed_thesaurus[entry]["http://purl.org/dc/terms/description"][0]
            del annotation["description"]["type"]

        if "http://www.w3.org/2004/02/skos/core#scopeNote" in parsed_thesaurus[entry]:
            annotation["note"] = parsed_thesaurus[entry]["http://www.w3.org/2004/02/skos/core#scopeNote"][0]["value"]

        if "http://www.w3.org/2004/02/skos/core#definition" in parsed_thesaurus[entry]:
            annotation["definition"] = parsed_thesaurus[entry]["http://www.w3.org/2004/02/skos/core#definition"][0]["value"]

        thesaurus.append(annotation)
    return thesaurus

def create_thesaurus_relations(parsed_thesaurus : dict, thesaurus_name : str, weights : dict) -> list:
    """
        Creates thesaurus relations from the raw thesaurus data fetched from openTheso

        :param parsed_thesaurus: Raw thesaurus, fetched from opentheso and parsed into a dict by the JSON library
        :type parsed_thesaurus: dict
        :param thesaurus_name: The name of the thesaurus, needed to know the full document ID and create edges
        :type thesaurus_name: str
        :param weights: A dictionary containing edge weight for each type of weight in the format {'narrower' : 1, 'broader' : 1, 'related' : 3, 'closeMatch' : 1.5,
        'exactMatch' : 0}
        :type weights: dict
        :returns: The list of edges created, that needs to be inserted into the ArangoDB collection. Each edge being stored as a dict
    """


    # I could have done it all inside of a single function, but I'm splitting for readability (in spite of performance) since
    # we won't do this often, and it is bottlenecked by the internet connexion anyway
    relations_list : list = []

    for entry in parsed_thesaurus:
        to_key : str = thesaurus_name + '/' +  entry.split("/")[-1] # Each entry defines the incoming relations, so we have the same _from key

        # We will create a relation for each entry in the broader, narrower, related, closematch and exactmatch list
        # TODO : demander a violette pour les relations specifiques du TH56

        broader : str = "http://www.w3.org/2004/02/skos/core#broader"
        narrower : str = "http://www.w3.org/2004/02/skos/core#narrower"
        related : str = "http://www.w3.org/2004/02/skos/core#related"
        close_match : str = "http://www.w3.org/2004/02/skos/core#closeMatch"
        exact_match : str = "http://www.w3.org/2004/02/skos/core#exactMatch"


        # The data being semi-structured we have to check if the key exists before doing anything with it

        if broader in parsed_thesaurus[entry]:
            for relation in parsed_thesaurus[entry][broader]:
                relations_list.append({
                    "_from" : thesaurus_name + '/' + relation["value"].split("/")[-1],
                    "_to" : to_key,
                    "type" : "broader",
                    "weight" : weights['broader']
                })

        if narrower in parsed_thesaurus[entry]:
            for relation in parsed_thesaurus[entry][narrower]:
                relations_list.append({
                    "_from" : thesaurus_name + '/' + relation["value"].split("/")[-1],
                    "_to" : to_key,
                    "type" : "narrower",
                    "weight" : weights['narrower']
                })

        if related in parsed_thesaurus[entry]:
            for relation in parsed_thesaurus[entry][related]:
                relations_list.append({
                    "_from" : thesaurus_name + '/' + relation["value"].split("/")[-1],
                    "_to" : to_key,
                    "type" : "related",
                    "weight" : weights['related']
                })

        if exact_match in parsed_thesaurus[entry]:
            for relation in parsed_thesaurus[entry][exact_match]:
                relations_list.append({
                    "_from" : thesaurus_name + '/' + relation["value"].split("/")[-1],
                    "_to" : to_key,
                    "type" : "exactMatch",
                    "weight" : weights['exactMatch']
                })

        if close_match in parsed_thesaurus[entry]:
            for relation in parsed_thesaurus[entry][close_match]:
                relations_list.append({
                    "_from" : thesaurus_name + '/' + relation["value"].split("/")[-1],
                    "_to" : to_key,
                    "type" : "closeMatch",
                    "weight" : weights['closeMatch']
                })

    return relations_list

def insert_raw_thesaurus(db : database.StandardDatabase, thesaurus : dict, name : str, weights : dict):
    """
    TODO : docstring
    """
    nodes_collection, edges_collection = get_collections(db, name)

    nodes_collection.truncate()
    edges_collection.truncate()

    theso_clean = {
        "nodes": create_thesaurus_dict(thesaurus),
        "relationships": create_thesaurus_relations(thesaurus, name, weights)
    }

    nodes_collection.insert_many(theso_clean['nodes'])
    edges_collection.insert_many(theso_clean['relationships'])

# And this is the main function, that can take care of everything with a simple configuration file

def create_thesaurus_from_config(config_path : str, weights : dict = None):
    """
    Creates all the needed thesaurus and insterts them into the correct ArangoDB instance and collections according to the given configuration
    the configuration schema is available in `config/theso-config-schema.json` and a boilerplate in `config/config-thesaurus-boilerplate.json`

    :param config_path: The path to the JSON configuration file
    :type config_path: str
    :param weights: An optional dictionary containing edge weight for each type of weight in the format {'narrower' : 1, 'broader' : 1, 'related' : 3, 'closeMatch' : 1.5, 'exactMatch' : 0}
    if nothing is given default weights will be used.
    :type weights: dict
    """
    if weights is None : # If no weights are defined we use the default ones (these are arbitrary)
        weights = {
            'narrower' : 1,
            'broader' : 1,
            'related' : 3,
            'closeMatch' : 1.5,
            'exactMatch' : 0
        }

    # Here we prepare the database API
    config = get_config(config_path, "config/theso-config-schema.json")
    theso_list = fetch_thesaurus(config["thesauri"])
    client: ArangoClient = ArangoClient(hosts=os.getenv("DB_ADDRESS"))

    # Connect to "_system" database as root user.
    # This returns an API wrapper for "_system" database.
    sys_db = client.db('_system', username='root', password='test')

    # Create the database associated with the thesaurus if it does not exist yet
    if not sys_db.has_database(os.getenv("DB_NAME")):
        sys_db.create_database(os.getenv("DB_NAME"))


    curr_db: database.StandardDatabase = client.db(name=os.getenv("DB_NAME"), username=os.getenv("DB_USER"),
                                                   password=os.getenv("DB_PASSWORD"))

    for i in range(len(theso_list)):
        if theso_list[i] is None:
            continue

        if config["thesauri"][i]["type"] == 'raw':
            insert_raw_thesaurus(curr_db, theso_list[i], config["thesauri"][i]["name"], weights)
        elif config["thesauri"][i]["type"] == 'graph':
            insert_graph_thesaurus(curr_db, config["thesauri"][i], theso_list[i])
            # Removed because it not relevant anymore (if you want inter thesaurus edges, you should use the raw import)
            """interThesaurusEdges += skipped
            all_new_nodes += added

            if interThesaurusEdges != [[]] and all_new_nodes != []:
                print(generate_inter_thesauri_edges(database, all_new_nodes, interThesaurusEdges))"""
        else:
            print("Thesaurus type not recognized")

def add_weights_to_collection(db : database.StandardDatabase, coll_name : str, weights : dict = None):
    """
    TODO : Docstring
    """
    if not db.has_collection(coll_name) :
        print(f"The given collection '{coll_name}' does not exist")
        return

    collection = db.collection(coll_name)

    if not collection.properties()['edge']: #Testing if it is an edge collection
        print(f"Cannot add weight on document collection {coll_name}")
        return

    if weights is None : # If no weights are defined we use the default ones (these are arbitrary)
        weights = {
            'narrower' : 1,
            'broader' : 1,
            'related' : 3,
            'closeMatch' : 1.5,
            'exactMatch' : 0
        }

    coll_cursor = collection.all()
    coll_dict = [_ for _ in coll_cursor]

    for edge in coll_dict:
        match edge['type']:
            case 'narrower':
                edge['weight'] = weights['narrower']
            case 'broader':
                edge['weight'] = weights['broader']
            case 'related':
                edge['weight'] = weights['related']
            case 'closeMatch':
                edge['weight'] = weights['closeMatch']
            case 'exactMatch':
                edge['weight'] = weights['exactMatch']
            case _:
                edge['weight'] = 1

    collection.update_many(coll_dict)

def add_weights_with_args(host: str, db_name: str, user: str, password: str, coll_name: str):
    client: ArangoClient = ArangoClient(hosts=host)
    db: database.StandardDatabase = client.db(db_name, username=user,
                                                  password=password)

    add_weights_to_collection(db, coll_name)

if __name__ == '__main__':
    testclient = ArangoClient("http://localhost:8529")

    testdatabase = testclient.db("TEATIME", "root", "test")

    add_weights_to_collection(testdatabase, "th15_relations")