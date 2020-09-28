import argparse


def parse_arguments():

    h_input = \
        "the input file or input directory to process," \
        + " take standard input if this is not specified."
    h_output = \
        "the output file or output directory to write the results to," \
        + " write to standard output if not specified; if INPUT is a" \
        + " directory then this should be a directory too, it will be " \
        + " created if it does not exist"
    h_terms = \
        "An external file with term offsets, if this option is used the" \
        + " script does not use its default way to collect terms"

    h_classifier = "switch off the classifier"
    h_verbose = "print some of the created data structures to standard output"
    h_limit = "the maximum number of files to process"

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", metavar='INPUT', help=h_input)
    parser.add_argument("-o", metavar='OUTPUT', help=h_output)
    parser.add_argument("--terms", metavar='TERMS', help=h_terms)
    parser.add_argument("--no-classifier", dest='classifier',
                        help=h_classifier, action="store_false")
    parser.add_argument("--verbose", help=h_verbose, action="store_true")
    parser.add_argument("--limit", help=h_limit, type=int)

    return parser.parse_args()
