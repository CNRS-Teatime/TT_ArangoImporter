import argparse, os, sys

from dotenv import load_dotenv

import thesaurusCreator, thesaurusCleaner, graphCreator, dumpImporter

def parse_command_line():
    """
    The function `parse_command_line` is a Python function that uses the `argparse` module to parse
    command line arguments and returns the parsed arguments.
    :return: The function `parse_command_line` returns the parsed command line arguments.
    """
    parser = argparse.ArgumentParser(description='ArangoDB data integration and graph creation from dumps and the openTheso API')

    # Thesaurus configuration json
    parser.add_argument('--thesaurus-config', '--thesaurus-path' ,'-t', type=str, help='The path to the thesaurus fetching configuration file')
    # Graph configuration json
    parser.add_argument('--graph-config', '--graph-path', '-g', type=str, help='The path to the graph creation configuration file')
    # Dump folder path
    parser.add_argument('--dump-folder', '--dump-path', '-d', type=str, help='The path a folder containing an arangoDB Dump as a JSON')
    # Cleanup boolean
    parser.add_argument('--cleanup', '-c', type=bool, default=False, help='Whether or not to perform cleanup after creating or populating a collection')

    parser.add_argument('--add-weights-to-coll', '-a', type=str, help='A collection, to whom you want to add default weights')

    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(1)

    return parser.parse_args()

def main():
    args = parse_command_line()
    load_dotenv()

    if args.thesaurus_config:
        thesaurusCreator.create_thesaurus_from_config(args.thesaurus_config)

    if args.graph_config:
        graphCreator.create_graph_from_config(args.graph_config)


    if args.add_weights_to_coll:
        thesaurusCreator.add_weights_with_args(os.getenv("DB_ADDRESS"), os.getenv("DB_NAME"), os.getenv("DB_USER"), os.getenv("DB_PASSWORD"), args.add_weights_to_coll)

    if args.dump_folder:
        dumpImporter.import_from_dump_main(os.getenv("DB_ADDRESS"), os.getenv("DB_NAME"), os.getenv("DB_USER"), os.getenv("DB_PASSWORD"), args.dump_folder)

    if args.cleanup:
        thesaurusCleaner.cleanup_database(os.getenv("DB_ADDRESS"), os.getenv("DB_NAME"), os.getenv("DB_USER"), os.getenv("DB_PASSWORD"))



if __name__ == "__main__":
    main()