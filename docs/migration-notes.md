# Migration from the original scripts

This repository consolidates the original standalone scripts for absorption,
CD, MCD, combined CD/MCD plotting, and extrema analysis.

Key changes:

- repeated plotting logic moved into reusable functions;
- hard-coded molecule names and filename prefixes removed;
- spectra with different grids are aligned by interpolation before subtraction;
- files with or without headers are accepted;
- generated files are separated from input data;
- peak information is written in CSV form;
- command-line options replace source-code editing;
- tests and continuous integration were added.

The original files can remain in the private repository history for provenance,
but they do not need to stay in the public working tree.
