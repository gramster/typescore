# typescore

__`typescore`__ generates typing completeness scores (and more) for a set of packages.

Usage:

```sh
  typescore [--packages <packages>] [--scores <scorefile>] [--sep <sep>] [--verbose] [<package>...]
  typescore --help
  typescore --version

Options:
  --packages <packages> File containing the list of packages.
  --scores <scorefile>  The output file (if not stdout).
  --sep <sep>           CSV column separator. [default: ,]
  -v, --verbose         Include package info in the output.
  -h, --help            Show this help.
  -V, --version         Show the version.
```

`typescore` uses pyright to score the typing completeness of a set of Python
packages. It reads this list from `<packages>` and writes the results to
`<scorefile>`. If errors prevent it from scoring a package it will set the
score to 0%.

The output has the form:

    package,typed,module,score,extra_columns

or, if `--verbose` is specified:

    package,version,typed,module,score,stub_package,package_description,extra_columns

`typed` is a Boolean and tells whether the package had a `py.typed` file.

Note: we only score top-level modules, not submodules. The assumption is
that scores for top-level modules would be reasonably representative of
the packages all-up.

`<packages>` should have one package name per line. It can be a CSV file with
the package name as the first column, in which case other columns will be
included in the score file output (the `extra_columns`). A typical extra column
might be the package rank on PyPI downloads.

While it would be useful to be able to measure the coverage scores on stub packages too, pyright does not support doing so. As a result, you should evaluate whether a stub package is better than the inline types for a package yourself beffore making use of it.


See [latest-scores.md](https://github.com/gramster/typescore/blob/main/latest-scores.md) for results in markdown form.
