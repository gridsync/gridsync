
Development Setup
-----------------

There are many ways to set up Python development environments; this documents one way using "virtualenv" environments.
Various kinds of dependencies are specified via the ``*.txt`` files in the ``./requirements/`` subdirectory.
To set up a development invironment in ``./venv``::

    virtualenv venv
    source venv/bin/activate
    python -m pip install -r requirements/gridsync.txt
    python -m pip install -r requirements/lint.txt

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


Vagrant
-------

There is a Vagrantfile in this repository which can be used to start some virtual machines for testing.


Windows 11
..........

To get a Windows-11 machine working on Debian "bullseye".
`sudo` is not specified below, but install commands need root.

- `apt install vagrant`
- install VirtualBox from Oracle (**not Debian**):
  - https://www.virtualbox.org/wiki/Downloads
  - Follow the instructions under "Linux distributions"
  - ultimately, `apt install virtualbox-6.1`
  - make sure to follow the instructions about groups and log out/in.

Upon a `vagrant up windows-11` in the root directory, I got a long Ruby traceback.
- `vagrant plugin install winrm`
- `vagrant plugin install winrm-elevated`

A `vagrant up window-11` now works from the home directory.

Note that these VM images are huge (20+ GiB) and by default use space in your home directory (twice).
To instuct Vagrant to use a different place, `export VAGRANT_HOME=/windows`
To instruct virtualbox to put the machine images elsewhere:
- `vboxmanage setproperty machinefolder /windows/virtualbox-vms`
(The latter can also be set to "default" which means to use `~/VirtualBox VMs`).
