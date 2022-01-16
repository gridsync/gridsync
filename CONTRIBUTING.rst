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
