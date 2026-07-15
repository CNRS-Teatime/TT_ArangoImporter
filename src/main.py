import os
from dotenv import load_dotenv
import thesaurusCreator, thesaurusCleaner, graphCreator, dumpImporter, POPImporter

def main():
    load_dotenv()

    if "THESO_CONFIG" in os.environ:
        thesaurusCreator.create_thesaurus_from_config(os.getenv("THESO_CONFIG"))

    if "DUMP_FOLDER" in os.environ:
        dumpImporter.import_from_dump_main(os.getenv("DB_ADDRESS"), os.getenv("DB_NAME"), os.getenv("DB_USER"), os.getenv("DB_PASSWORD"), os.getenv("DUMP_FOLDER"))

    if "POP_DATA_LOCATION" in os.environ:
        POPImporter.insert_and_align_palissy_merimee_joconde_data(os.getenv("POP_DATA_LOCATION"))

    if "GRAPH_CONFIG" in os.environ:
        graphCreator.create_graph_from_config(os.getenv("GRAPH_CONFIG"))

    if "CLEANUP" in os.environ:
        thesaurusCleaner.cleanup_database(os.getenv("DB_ADDRESS"), os.getenv("DB_NAME"), os.getenv("DB_USER"), os.getenv("DB_PASSWORD"))

    if "COLL_TO_ADD_WEIGHTS_TO" in os.environ:
        thesaurusCreator.add_weights_with_args(os.getenv("DB_ADDRESS"), os.getenv("DB_NAME"), os.getenv("DB_USER"), os.getenv("DB_PASSWORD"), os.getenv("COLL_TO_ADD_WEIGHTS_TO"))


if __name__ == "__main__":
    main()