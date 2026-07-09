import csv, os
from dotenv import load_dotenv
from arango import ArangoClient, database

WORKDIR = os.getenv("POP_DATA_LOCATION")

def fetch_alignment_dict(filename : str = "key_desc_pairs.csv") -> dict:
    """
    Fetches the alignment chart between each databases keys and W7 questions

    :param filename: The name of the csv file containing the alignment dictionnary. Default is `key_desc_pairs.csv`
    :type filename: str

    :returns: a dictionnary in the form {
        "merimee" : {key : w7questions, ...},
        "palissy" : {key : w7questions, ...},
        "joconde" : {key : w7questions, ...}
    }
    """

    result : dict = {
        "merimee" : {},
        "palissy" : {},
        "joconde" : {}
    }

    with open(f"{WORKDIR}/{filename}") as f:
        # header of csv file : source, key, description, W7

        reader = csv.DictReader(f) #allows us to retrieve via header instead of position in the line (much more resilient)
        for line in reader:
            result[line['source']][line['key']] = line['W7'].upper()

    return result

def convert_POP_database(database: str,alignment: dict, filename : str):
    """
    Reads the palissy csv file, convert it to a W7 aligned arangoDB ready list of document.

    :param alignment: A dictionnary created using `fetch_alignment_dict()` containing information about wich palissy key goes into which W7 question
    :type alignment: dict
    :param filename: The name of the csv file containing the palissy objects. Default is `palissy_ndp.csv`
    :type filename: str

    :returns: a list of palissy objects in the format
        {
            "_KEY": Str,
            "WHO": {
                [KEY] : {
                    "description" ": string,
                    "value" : val
                },
                ...
            },
            "WHY": {
                same structure as WHO for each question
            },
            "WHERE": {},
            "WHEN": {},
            "HOW": {},
            "WHICH": {},
            "WHAT": {}
        }
    Each W7 question encapsulate original key value pairs present in the palissy object along with the natural language description of it
    """
    if database not in alignment.keys():
        print("database not in alignment chart")
        return None

    result = []
    desc = {}

    with (open(f"{WORKDIR}/{filename}") as f):
        reader = csv.DictReader(f)

        for line in reader:
            if reader.line_num == 2:
                desc = line
            else :
                translation = {
                    "_key": line["REF"],
                    "WHO": {},
                    "WHY": {},
                    "WHERE": {},
                    "WHEN": {},
                    "HOW": {},
                    "WHICH": {},
                    "WHAT": {}
                }
                for key in line:
                    translation[alignment[database][key].split(',')[0]][key] = {
                        "description" : desc[key],
                        "value" : line[key]
                    }

                result.append(translation)

    return result


def insert_into_arango(collection_name : str, documents : list):
    client: ArangoClient = ArangoClient(hosts=os.getenv("DB_ADDRESS"))
    db: database.StandardDatabase = client.db(os.getenv("DB_NAME"), username=os.getenv("DB_USER"),
                                                      password=os.getenv("DB_PASSWORD"))

    if db.has_collection(collection_name):
        collection: database.StandardCollection = db.collection(collection_name)
        collection.truncate()
    else:
        collection: database.StandardCollection = db.create_collection(collection_name)

    collection.insert_many(documents)


if __name__ == "__main__":
    load_dotenv()
    WORKDIR = os.getenv("POP_DATA_LOCATION")
    alignment_dict = fetch_alignment_dict()

    palissy = convert_POP_database("palissy", alignment_dict, "palissy_ndp.csv")
    insert_into_arango("palissy", palissy)

    merimee = convert_POP_database("merimee", alignment_dict, "merimee_ndp.csv")
    insert_into_arango("merimee", merimee)

    joconde = convert_POP_database("joconde", alignment_dict, "joconde_ndp.csv")
    insert_into_arango("joconde", joconde)

