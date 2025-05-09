# UNIX Password Manager -> `Bitwarden`

This repository is a collection of python scripts alongside some bash utilities
to help manage the migration from the UNIX password manager, `pass`, to
`Bitwarden`.

The python scripts of interest are at the time of writing at the root of the
repository and each one contains a description of its purpose alongside the
requirements it needs to run. Note that if you have `uv` installed, you should
be able to just execute the script of interest it will setup a `virtualenv` for
you and install any necessary dependencies.

* `passbankcards2bitwarden.py`: Convert bank card details from a `pass`-compatible
    directory structure to `Bitwarden`.
* `passnotes2bitwarden.py`: Convert notes from a `pass`-compatible directory
    structure to `Bitwarden`.
* `pass2bitwarden.py`: Convert passwords from a `pass`-compatible directory
  structure to `Bitwarden`.

As mentioned above, the `share/` directory contains some bash and python scripts
that may be useful in the migration process. They constitute more of a
scratchpad for the various functions I used  during the migration and less than
polished scripts to use out of the box. They are not required to run any of the
aforementioned top-level scripts.
