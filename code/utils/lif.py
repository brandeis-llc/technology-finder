"""lif.py

NOTE: this script was originally adapted from the tarsqi toolkit (utilities/lif.py).

Interface to the LAPPS Interchance Format and to the LAPPS Data container.

Contains code to:

- Read JSON-LD strings for containers and LIF objects
- Export Containers and LIF objects to JSON-LD strings

To read and write a data container:

>>> container = Container(infile)
>>> container.write(outfile, pretty=True)

To read and write a LIF object:

>>> lif = LIF(infile)
>>> lif.write(outfile, pretty=True)

Normaly there would be some manipulation of the LIF object between reading and
writing, most typically by adding views.

On the command line:

$ python lif.py --container INFILE OUTFILE
$ python lif.py --lif INFILE OUTFILE


"""

import os
import sys
import codecs
import json
import subprocess


class LappsObject(object):

    def __init__(self, json_file, json_string, json_object):
        self.json_file = json_file
        self.json_file = json_string
        self.json_object = json_object
        if json_file is not None:
            self.json_string = codecs.open(json_file).read()
            self.json_object = json.loads(self.json_string)
        elif json_string is not None:
            self.json_string = json_string
            self.json_object = json.loads(self.json_string)
        elif json_object is not None:
            self.json_string = None
            self.json_object = json_object

    def write(self, fname=None, pretty=False):
        # first update the json object for those case where it has been changed
        json_obj = self.as_json()
        if pretty:
            s = json.dumps(json_obj, sort_keys=True, indent=4, separators=(',', ': '))
        else:
            s = json.dumps(json_obj)
        fh = sys.stdout if fname is None else codecs.open(fname, 'w')
        fh.write(s + "\n")


class LIF(LappsObject):

    def __init__(self, json_file=None, json_string=None, json_object=None):
        LappsObject.__init__(self, json_file, json_string, json_object)
        self.context = "http://vocab.lappsgrid.org/context-1.0.0.jsonld"
        self.metadata = {}
        self.text = Text()
        self.views = []
        if self.json_object is not None:
            self.metadata = self.json_object['metadata']
            self.text = Text(self.json_object['text'])
            for v in self.json_object['views']:
                self.views.append(View(json_obj=v))

    def __str__(self):
        views = [(view.id, len(view.annotations)) for view in self.views]
        return "<LIF with views {}>".format(' '.join(["%s:%s" % (i, c) for i, c in views]))

    def get_view(self, identifier):
        for view in self.views:
            if view.id == identifier:
                return view
        return None

    def as_json(self):
        d = {"@context": self.context,
             "metadata": self.metadata,
             "text": self.text.as_json(),
             "views": [v.as_json() for v in self.views]}
        return d

    def as_json_string(self):
        return json.dumps(self.as_json(), sort_keys=True, indent=4, separators=(',', ': '))


class Text(object):

    def __init__(self, json_obj=None):
        self.language = 'en'
        self.value = ''
        if json_obj is not None:
            self.language = json_obj.get('language')
            self.value = json_obj.get('@value')

    def __str__(self):
        return "<Text lang={} length={:d}>".format(self.language, len(self.value))

    def as_json(self):
        d = {"@value": self.value}
        if self.language is not None:
            d["language"] = self.language
        return d


class View(object):

    def __init__(self, id=None, json_obj=None):
        self.id = id
        self.metadata = { "contains": {} }
        self.annotations = []
        self.annotations_idx = {}
        if json_obj is not None:
            self.id = json_obj['id']
            self.metadata = json_obj['metadata']
            for a in json_obj['annotations']:
                self.annotations.append(Annotation(a))

    def __len__(self):
        return len(self.annotations)

    def __str__(self):
        return "<View id={} with {:d} annotations>".format(self.id, len(self.annotations))

    def index(self):
        """Create an dictionary of all annotations in the view with the annotations
        indexed on their identifiers."""
        self.annotations_idx = {}
        for annotation in self.annotations:
            self.annotations_idx[annotation.id] = annotation

    def get_annotation(self, anno_id):
        return self.annotation_dx.get(anno_id)

    def as_json(self):
        d = {"id": self.id,
             "metadata": self.metadata,
             "annotations": [a.as_json() for a in self.annotations]}
        return d

    def pp(self):
        print(self)
        for contains in self.metadata["contains"].keys():
            print('    {}'.format(contains))


class Annotation(object):

    def __init__(self, json_obj):
        self.id = json_obj['id']
        self.type = json_obj['@type']
        self.start = json_obj.get("start")
        self.end = json_obj.get("end")
        self.target = json_obj.get("target")
        self.text = None
        self.features = {}
        for feat, val in json_obj.get("features", {}).items():
            self.features[feat] = val

    def __str__(self):
        text = self.get_text()
        text = '' if text is None else text.replace("\n", "\\n")
        return "<{} {} {}-{} '{}'>".format(os.path.basename(self.type), self.id,
                                           self.start, self.end, text)

    def get_text(self):
        """Return the text string from the text instance variable or the text feature,
        returns None of there is no string available."""
        if self.text is not None:
            return self.text
        return self.features.get('text')

    def get_feature(self, feature):
        return self.features.get(feature)

    def as_json(self):
        d = {"id": self.id, "@type": self.type, "features": self.features}
        if self.start is not None:
            d["start"] = self.start
        if self.end is not None:
            d["end"] = self.end
        if self.target is not None:
            d["target"] = self.target
        return d


class IdentifierFactory(object):

    @classmethod
    def new_id(cls, tag):
        cls.identifiers[tag.name] = cls.identifiers.get(tag.name, 0) + 1
        return "{}{:d}".format(tag.name, cls.identifiers[tag.name])


def compare(file1, file2):
    """Output file could have a very different ordering of json properties, so
    compare by taking all the lines, normalizing them (stripping space and commas)
    and sorting them."""
    lines1 = sorted(codecs.open(file1).readlines())
    lines2 = sorted(codecs.open(file2).readlines())
    with codecs.open("comp1", 'w') as c1, codecs.open("comp2", 'w') as c2:
        c1.write("\n".join([l.strip().rstrip(',') for l in lines1]))
        c2.write("\n".join([l.strip().rstrip(',') for l in lines2]))
    subprocess.call(['echo', '$ ls -al comp?'])
    subprocess.call(['ls', '-al', "comp1"])
    subprocess.call(['ls', '-al', "comp2"])
    subprocess.call(['echo', '$ diff', 'comp1', 'comp2'])
    subprocess.call(['diff', 'comp1', 'comp2'])


if __name__ == '__main__':

    input_type, infile, outfile = sys.argv[1:4]

    if input_type == '--lif':
        lapps_object = LIF(infile)
    elif input_type == '--container':
        lapps_object = Container(infile)

    # doesn't print this quite as I like it, for a view it first does the
    # annotations, then the id and then the metadata
    lapps_object.write(outfile, pretty=True)

    # test by comparing input and output
    compare(infile, outfile)
