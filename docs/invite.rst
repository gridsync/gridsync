Invite codes
============

The SPAKE2-based `magic-wormhole <http://magic-wormhole.io>`_ library provides a means of securely exchanging sensitive materials via one-time-use human-pronounceable codes. This is currently used in Gridsync to facilitate the hitherto unfriendly action of joining a Tahoe-LAFS storage grid: rather than having to receive and paste, e.g., a lengthy introducer fURL into a configuration file, a user may instead enter a shorter "invite code" (e.g., ``1-rebellion-concert``) provided to the user by another party (such as the operator of a storage grid). When entered correctly, the invite code is sufficient to open a secure channel from which the required configuration information is received from the other party.

Currently, Gridsync expects the information received through a wormhole to fulfill the parameters for the ``tahoe create-client`` command, encoded in JSON format (as seen in the example below). Assuming a Tahoe-LAFS install of version 1.12.1 or higher, the following options will be considered valid:

.. code-block::

    nickname
    introducer
    shares-needed
    shares-happy
    shares-total

Any options other than the above will be ignored by the receiving end.


Example
-------

If Alice (the operator of a storage test grid) wishes to invite Bob (an end user) to join a grid, she could run the following script on her computer, using ``wormhole`` to generate an "invite code" to give to Bob:

.. code-block::

    #!/bin/sh

    JSON=\
    '{
        "nickname": "TestGrid",
        "introducer": "pb://3kzbib3v5i7gmtd2vkjujfywqiwzintw@test.gridsync.io:44800/2qdq2buyzmwq6xuxl2sdzyej5vswhkqs",
        "shares-needed": "1",
        "shares-happy": "1",
        "shares-total": "1"
    }'

    echo $JSON | wormhole send --text -


This might produce the following output on Alice's computer:


.. code-block::

    Reading text message from stdin..
    Sending text message (202 Bytes)
    On the other computer, please run: wormhole receive
    Wormhole code is: 1-insincere-christmas


When Bob types the above code (``1-insincere-christmas``) into his Gridsync desktop application, a new Tahoe-LAFS client will be automatically created and configured with the expected parameters:

``--introducer=pb://3kzbib3v5i7gmtd2vkjujfywqiwzintw@test.gridsync.io:44800/2qdq2buyzmwq6xuxl2sdzyej5vswhkqs --shares-needed=1 --shares-happy=1 --shares-total=1 --nickname=TestGrid``

Bob, of course, does not see any of this; the only thing that Bob needs to know or see in order to join the grid is the invite code provided to him by Alice (``1-insincere-christmas``).


In the future, invite codes will be extended to provide additional information (e.g., allowing grid operators to specify an identifying icon) and may be used for additional purposes (e.g., sharing files or folders between users).

