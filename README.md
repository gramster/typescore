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

    package,module,score,extra_columns

or, if --verbose is specified:

    package,version,module,score,package_description,extra_columns

Note: we only score top-level modules, not submodules. The assumption is
that scores for top-level modules would be reasonably representative of
the packages all-up.

<packages> should have one package name per line. It can be a CSV file with
the package name as the first column, in which case other columns will be
included in the SCOREFILE output ('extra_columns'). A typical extra column
might be the package rank on PyPI downloads.
