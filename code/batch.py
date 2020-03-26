"""batch.py

$ python3 batch.py --process-directory INDIR OUTDIR N?

Process all files in INDIR and save the results in OUTDIR. Process only N files
if the third argument is given, the default is to process all files.


TODO:

- LIF is not the most space-friendly format and there are cases where the LIF
  output can be more than 100 times bigger than the text input. May want to add
  a flag to compress the output file. For now we can compress manually if
  diskspace is an issue but we should make sure that consumers can read the
  compressed data.

"""

import os
import sys
import time

import main
from utils.misc import timestamp


def process_directory(indir, outdir, n):
    main.load_spacy()
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    t0 = time.time()
    with open('data/logs/log-%s.txt' % timestamp(), 'w') as log:
        log.write("$ python3 %s\n\n" % ' '.join(sys.argv))
        fnames = list(sorted(os.listdir(indir)))
        for c, fname in enumerate(fnames[:n]):
            infile = os.path.join(indir, fname)
            outfile = os.path.join(outdir, fname)
            log.write("%05d  %s  %s\n" % (c + 1, timestamp(), fname))
            try:
                main.TechnologyFinder(infile, outfile).run()
            except Exception as e:
                log.write('ERROR: %s\n' % e)
        log.write("\ntime elapsed: %s seconds\n" % int(time.time() - t0))


if __name__ == '__main__':

    if sys.argv[1] == '--process-directory':
        indir = sys.argv[2]
        outdir = sys.argv[3]
        n = int(sys.argv[4]) if len(sys.argv) > 4 else sys.maxsize
        process_directory(indir, outdir, n)
