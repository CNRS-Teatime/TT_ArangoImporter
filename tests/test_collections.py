# noinspection PyPackageRequirements
import unittest, docker, json
from arango import ArangoClient, database
from docker import DockerClient

from src import dumpImporter, thesaurusCreator


class MyTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Creating a new empty ArangoDB container to run the test safely as well as a TEST database
        Connecting to it through the arango API
        """
        image_name : str = "arangodb/enterprise:3.12.6.1"
        env : dict = {'ARANGO_ROOT_PASSWORD':'test'}
        ports : dict = {'8529':'8530'}
        cls._connection : DockerClient = docker.from_env()
        cls._connection.containers.run(image_name, name="TestCollections", detach=True, environment=env, ports=ports)

        cls._credentials: dict = {
            "host": "http://localhost:8530",
            "username": "root",
            "password": "test",
            "database": "TEST"
        }
        cls._client = ArangoClient(cls._credentials['host'])

        sys_db : database.StandardDatabase = cls._client.db('_system', username='root', password='test')

        if not sys_db.has_database(cls._credentials['database']):
            sys_db.create_database(cls._credentials['database'])

        cls._arango_database : database.StandardDatabase = cls._client.db(cls._credentials['database'], username=cls._credentials['username'], password=cls._credentials['password'])

    @classmethod
    def tearDownClass(cls):
        """
        Cleaning up the test container and Arango API Wrapper
        """
        cls._client.close()

        cls._connection.containers.get("TestCollections").remove(force=True)
        cls._connection.close()



    def test_insertion_raw(self):

        with open("data/test/th13-raw.json") as file:
            theso: dict = json.load(file)

            weights = {
                'narrower': 1,
                'broader': 1,
                'related': 3,
                'closeMatch': 1.5,
                'exactMatch': 0
            }

            thesaurusCreator.insert_raw_thesaurus(self._arango_database, theso, "TESTRAW", weights)

        self.assertTrue(True)

    def test_insertion_graph(self):
        theso_config : dict = { # We can get by with just a name since we don't have to fetch anything
            "name" : "TEST2"
        }

        with open("data/test/th13.json") as file:
            theso : dict = json.load(file)

            skipped, added = thesaurusCreator.insert_graph_thesaurus(self._arango_database, theso_config, theso)

            self.assertEqual(len(skipped), 1130)
            self.assertEqual(len(added), 2249)

    def test_dump(self):

        dumpImporter.import_from_dump(self._arango_database, "data/test/Dump")

        collections = self._arango_database.collections()
        collections = [coll['name'] for coll in collections]

        self.assertTrue('aioli_objects' in collections)
        self.assertTrue('aioli_relations' in collections)
        self.assertTrue('aioli_users' in  collections)

        test_result = self._arango_database.aql.execute(
            "FOR doc IN aioli_objects FILTER doc._key == '00035fcebac142eb' RETURN doc")
        test_result = [_ for _ in test_result]

        del test_result[0]['_rev']

        self.assertDictEqual(test_result[0],
                         {"_key": "00035fcebac142eb", "_id": "aioli_objects/00035fcebac142eb", "type": "Region",
                           "name": "tmp_reg", "project": "65fae48a5ab9a", "layer": "dc866bc786f90c65", "owner": "MOE",
                           "material": "blue", "description": {}, "color": "#173e8c"},
                         msg="Missing information in the collections")


if __name__ == '__main__':
    unittest.main()
