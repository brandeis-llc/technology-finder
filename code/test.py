
import argparse

parser = argparse.ArgumentParser()
input_help = "the file to process"
output_help = "the output file, print to standard output if not specified"
verbose_help = "print some created data structures to standard output"
parser.add_argument("--input", help=input_help, required=True)
parser.add_argument("--output", help=output_help)
parser.add_argument("--verbose", help=verbose_help, action="store_true")
args = parser.parse_args()

print(args)
