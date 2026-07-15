# ArangoDB importer
***

## Description
This tool is an importer for ArangoDB that fetches and validate from Openthesaurus, Aïoli and POP databases. It is a prerequisite for most experiments in the PRIME TEATIME PhD thesis.

## Prerequisites

This utility does not generate or manage you ArangoDB instance. You need to refer to ArangoDB's [documentation](https://docs.arango.ai/arangodb/stable/get-started/). We recommend using the dockerised version of ArangoDB.

## Installation

Python 3.12 is required.

We recommend using a virtual python environment through the [venv](https://docs.python.org/3/library/venv.html) python package. Simply replace `{foldername}` in the following command with the desired environment name (for ex Debug).
```bash
python3 -m venv {foldername}
```

Then activate the virtual environment :

### Unix/MacOS

```bash
source {foldername}/bin/activate
```

### Windows

```bash
./{foldername}/bin/activate
```

Finaly you can install the dependencies listed in requirements.txt via this command

```bash
python3 -m pip install -r requirements.txt
```

More info here : https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/

### Environment

A .env file needs to be created to define the arangoDB adress and credentials. An example can be found in the `.env-BOILERPLATE` file. Optional variable allow for choosing what type of information will be imported in the database. For example you could set only `THESO_CONFIG` and `POP_DATA_LOCATION` to create a database with only those information. Unset variables will be skipped.

```dotenv
#Mandatory
DB_ADDRESS="http://localhost:8529"
DB_NAME="NAME"
DB_USER="USERNAME"
DB_PASSWORD="PASSWORD"
#Optional
THESO_CONFIG="config/config-thesaurus-xp.json"
GRAPH_CONFIG="config/config-graph-xp.json"
POP_DATA_LOCATION="data/POP"
DUMP_FOLDER="data/DumpArango"
CLEANUP=true
COLL_TO_ADD_WEIGHTS_TO="FOO"
```

## Usage
Here is a description of each environment variables

| Variable               | Description                                                        | Example              |
|------------------------|--------------------------------------------------------------------|----------------------|
| THESO_CONFIG           | The path to the thesaurus fetching configuration file              | config/thesauri.json |
| GRAPH_CONFIG           | The path to the graph creation configuration file                  | config/graphs.json   |
| POP_DATA_LOCATION      | The path to a folder containing POP data as CSV files              | data/pop             |
| DUMP_FOLDER            | The path to the graph creation configuration file                  | path/to/dump         |
| COLL_TO_ADD_WEIGHTS_TO | An existing weight collection, where default weights will be added | th15_relations       |
| CLEANUP                | Whether or not to perform cleanup after import                     | true                 |

With the correct .env file and if the requirements.txt has been used to set up the python virtual environment:

```bash
python3 src/main.py
```

## Feature specific information

### Opentheso importer

The opentheso importer uses json configuration files and the opentheso REST API to fetch graph data from an opentheso instance, clean it, 
and store it in a dedicated arangoDB Graph Database.
It is used with the `--thesaurus-config` option.

A config file is composed as follows (boilerplate information inside the example, it wont work as is) : 

```json
{
    "thesauri" : [
        {
            "name" : "PREFERED NAME 1",

            "source" : "https://your.web.link/openapi/v1/graph/getData?dThesoConcept=ID",
            "type" : "graph" 
        },
        {
            "name" : "PREFERED NAME 2",
            "source" : "https://your.web.link/openapi/v1/thesaurus/ID",
            "type" : "raw" 
        }
    ]
}
```

The JSON Schema is available in `theso-config-schema.json`. All config files given to the tool are validated against it.
The `thesauri` section is a list of graphs to import to ArandoDB, consisting of the associated *GET* Request in the `source` field, a name and the type of import that the Request will return. There are two types of import that are supported (unsupported types are ignored) :

- `'raw'` : These are thesaurus that are not pre-formated as a graph by the opentheso instance. They usually contain much more information and are faster to fetch from the server. This is the recommended format. In opentheso, they are the requests that end with `/thesaurus/ID`
- `'graph'` : These are the pre-formated graphs that represent a thesaurus. They are missing some information. In opentheso, they are the requests that end with `/graph/getData?dThesoConcept=ID`

The database will be created if it does not exist if you have the default ArangoDB ROOT username and password, otherwise you will have to use an ==already existing database==.

> You can use the `config-BOILERPLATE.json` file and replace the values with your own to easily start creating a custom config file.

### Graph maker

The graph maker will initialize ArangoDB graphs based on a configuration file, specifying edge and document collections for each graph.
Its purpose is to increase repoducibility, and reduce human errors during experimentations. It is used
with the `--graph-config option`

A config file is composed as follows (boilerplate information inside the example, it wont work as is) :
```JSON
{
    "graphs" : [
        {
            "name" : "PREFERED NAME 1",
            "relations" : [
                {
                    "edge_collection" : "EDGE COLLECTION NAME",
                    "from_vertex_collections" : [
                        "COLLECTION 1",
                        "COLLECTION 2"
                    ],
                    "to_vertex_collections" : [
                        "COLLECTION 3",
                        "COLLECTION 4"
                    ]
                }
            ]
        },
        {
            "name" : "PREFERED NAME 2",
            "relations" : [
                {
                    "edge_collection" : "EDGE COLLECTION NAME",
                    "from_vertex_collections" : [
                        "COLLECTION 1",
                        "COLLECTION 2"
                    ],
                    "to_vertex_collections" : [
                        "COLLECTION 3",
                        "COLLECTION 4"
                    ]
                }
            ]
        }
    ]
}
```

The JSON Schema is available in `graph-config-schema.json`. All config files given to the tool are validated against it.
Each graph entry asks for a name, a singular edge collection and two list of incoming and outgoing collections (which can be identical). The collections must already exist in the database, otherwise the graph will not be created.

You can use `config-graph-BOILERPLATE.json` as a base to create your own configuration files.

### Dump importer

The dump impoter will populate a database using an arangoDB dump, contained in a given folder. A dump is simply a collection
of JSON files, in the arangoDB format, which can be obtained by fetching an arangoDB database.
Its primary use is saving Database states for later use.

It is used with the `DUMP_PATH` environment variable.

### POP data importer

Data used in experiments can be found in `data/POP`
For the pop data to be importer correctly the folder needs to follow this template :

```
.
├── joconde_ndp.csv
├── key_desc_pairs.csv
├── merimee_ndp.csv
└── palissy_ndp.csv
```

The joconde, merimee and palissy csv files were extracted from https://pop.culture.gouv.fr/recherche, with the query "Notre dame de Paris", filtering each time for the given database/source.

## Roadmap

- [x] [Opentheso](https://opentheso.hypotheses.org/introduction) to ArangoDB importer
- [x] [Aioli](https://www.map.cnrs.fr/fr/recherche/projets/aioli/) to ArangoDB importer
  * It is covered by the dump importer, as Aiolï's API is not adapted to our use case
- [x] POP databases importer
  - [x] Merimee
  - [x] Palissy
  - [x] Joconde

## License
This work is licenced under GNU GPL v3.0

## Project status
Ongoing
