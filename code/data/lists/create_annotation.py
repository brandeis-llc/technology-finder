"""create_annotation.py

Take a terms file ordered on frequency and write the terms to an annotation file
using the first n lines of the file.

"""


TERMS_FILE = '/DATA/ttap/processed/terms-nr-SensorData.txt'
ANNOTATION_FILE = 'labels-SensorData.txt'
LINES_TO_USE = 1000


def create_annotation_file(terms_file, annotation_file, lines_to_use):
    with open(terms_file) as terms, open(annotation_file, 'w') as anno:
        for _i in range(LINES_TO_USE):
            line = terms.readline()
            anno.write("\t%s" % line)
    

if __name__ == '__main__':
    
    create_annotation_file(TERMS_FILE, ANNOTATION_FILE, LINES_TO_USE)
