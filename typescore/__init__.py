"""
typescore - generate typing completeness scores for a set of packages

Usage:
  typescore <packages> [--verbose] [--scores <scorefile>] [--sep <sep>]
  typescore --help
  typescore --version

Options:
  --scores <scorefile>  The output file. [default: scores.csv]
  --sep <sep>           CSV column separator. [default: ,]
  --verbose             Include package info in the output.
  --help                Show this help.
  --version             Show the version.

typescore uses pyright to score the typing completeness of a set of Python
packages. It reads this list from <packages> and writes the results to
<scorefile>. If errors prevent it from scoring a package it will set the
score to 0%.

The output has the form:

    package,typed,module,score,extra_columns

or, if --verbose is specified:

    package,version,typed,module,score,package_description,extra_columns

'typed' is a Boolean and tells whether the package had a py.typed file.

Note: we only score top-level modules, not submodules. The assumption is
that scores for top-level modules would be reasonably representative of
the packages all-up.

<packages> should have one package name per line. It can be a CSV file with
the package name as the first column, in which case other columns will be
included in the score file output ('extra_columns'). A typical extra column
might be the package rank on PyPI downloads.
"""

__version__ = '0.1'


from docopt import docopt
from .typescore import compute_scores


def main():
    arguments = docopt(__doc__, version=__version__)
    packagesfile = arguments['<packages>']
    scores = arguments['--scores']
    verbose = arguments['--verbose']
    sep = arguments['--sep']
    compute_scores(packagesfile, scores, verbose, sep)

