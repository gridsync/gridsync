
Development Setup
-----------------

Working with a virtualenv you may install various kinds of dependencies via the ``*.txt`` files in the ``./requirements/`` subdirectory.
For example::

    virtualenv venv
    ./venv/bin/python -m pip install -r requirements/gridsync.txt
    ./venv/bin/python -m pip install -r requirements/lint.txt

To run the linter::

    tox -e lint

To fix errors that the linter would discover, run::

    bash scripts/lint-fix.sh

Note that this will edit your working copy (but will not do any git operations).


Updating depdencies
-------------------

zkapauthorizer
...............

We depend on a pinned commit of zkapauthorizer.
To update to the latest commit, run

.. code:: shell

   tox -e update-github-repo -- --branch main requirements/tahoe-lafs.json
   tox -e update-hashes

This will update the pinned commit, and regenerate the pinned dependencies.
It is also possible to pass ``pull/<pr-number>/head`` to test against a specific PR.

magic-folder
............

We depend on a pinned commit of magic-folder.
To update to the latest commit, run

.. code:: shell

   tox -e update-github-repo -- --branch main requirements/magic-folder.json

This will update the pinned commit.
It is also possible to pass ``pull/<pr-number>/head`` to test against a specific PR.

nix
...

We maintain a `Nix flake <https://nixos.wiki/wiki/Flakes>`_ that provides a partial *development* environment for GridSync.

You can expect to be able to run most tox environments from within the environment provided by

.. code:: shell

   nix develop

Some development dependencies
(mostly Python and the native library dependencies of Qt)
are taken from a pinned version of nixpkgs.
To update the version of nixpkgs used run

.. code:: shell

   nix flake lock --update-input nixpkgs

And then commit the changes to ``flake.nix`` and ``flake.lock``.
Each other input (see ``nix flake metadata``) can be updated similarly.

One constraint to be aware of is that ``mach-nix`` generally will not run if the pinned ``pypi-deps-db`` input is older than the pinned ``nixpkgs`` input.
