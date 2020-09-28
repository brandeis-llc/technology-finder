"""lif.py

NOTE: this script was originally adapted from the tarsqi toolkit (utilities/lif.py).

Interface to the LAPPS Interchance Format.

Contains code to:

- Read JSON-LD strings for LIF objects
- Export LIF objects to JSON-LD strings

To read and write a LIF object:

>>> lif = LIF(infile)
>>> lif.write(outfile, pretty=True)

Normaly there would be some manipulation of the LIF object between reading and
writing, most typically by adding views.

On the command line:

$ python lif.py INFILE OUTFILE

This will just copy the file and test whether input and output are similar.

"""

import os
import sys
import time
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
        self.metadata = { "timestamp": time.asctime(), "contains": {} }
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

    def add_contains(self, annotation_type):
        self.metadata.setdefault('contains', {})[annotation_type] = {}

    def index(self):
        """Create an dictionary of all annotations in the view with the annotations
        indexed on their identifiers."""
        self.annotations_idx = {}
        for annotation in self.annotations:
            self.annotations_idx[annotation.id] = annotation

    def get_annotation(self, anno_id):
        return self.annotation_dx.get(anno_id)

    def as_json(self):
        return {"id": self.id,
                "metadata": self.metadata,
                "annotations": [a.as_json() for a in self.annotations]}

    def pp(self):
        print(self)
        for contains in self.metadata["contains"].keys():
            print('    {}'.format(contains))


class Annotation(object):

    """An instance of this is very similar to an annotation in LIF, but one
    difference is that there is a text instance variable."""

    def __init__(self, json_obj):
        self.id = json_obj['id']
        self.type = json_obj['@type']
        self.start = json_obj.get("start")
        self.end = json_obj.get("end")
        self.target = json_obj.get("target")
        features = json_obj.get('features', {})
        self.text = features.get('text')
        self.features = { f: a for (f, a)  in features.items() }

    def __str__(self):
        text = self.text
        text = '' if text is None else text.replace("\n", "\\n")
        #if not text and 'text' in self.features:
        #    text = self.features['text'].strip()
        offsets = '' if self.start is None else "%s-%s " % (self.start, self.end)
        return "<Annotation type={} id={} {}'{}'>".format(
            os.path.basename(self.type), self.id, offsets, text)

    def get_feature(self, feature):
        return self.features.get(feature)

    def as_json(self):
        d = {"id": self.id, "@type": self.type, "features": self.features}
        for attr in ('start', 'end', 'target'):
            val = getattr(self, attr)
            if val is not None:
                d[attr] = val
        if self.text is not None:
            d["features"]['text'] = self.text
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
    lines1 = [l.replace(' ', '').strip().rstrip(',') for l in lines1]
    lines2 = [l.replace(' ', '').strip().rstrip(',') for l in lines2]
    print("Testing equality of input and output file modulo spaces and final commas")
    if lines1 == lines2:
        print("==> lines in input and output file are identical")
    else:
        print("==> lines in input and output file are not identical")


if __name__ == '__main__':

    infile, outfile = sys.argv[1:3]
    lapps_object = LIF(infile)

    # doesn't print this quite as I like it, for a view it first does the
    # annotations, then the id and then the metadata
    lapps_object.write(outfile, pretty=True)

    # test by comparing input and output
    compare(infile, outfile)
