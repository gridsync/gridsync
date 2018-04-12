"Cheat codes"
=============

What is a "cheat code"?
-----------------------

A "cheat code" is effectively an [invite code](https://github.com/gridsync/gridsync/blob/master/docs/invite-codes.md) that does not depend upon the successful completion of a `magic-wormhole` exchange; by entering a known "cheat code" into a Gridsync client, end users can join a storage grid without relying upon another "sending" party to facilitate the invitation process.

"Cheat codes" are thus intended to provide an easy means for end users to join public storage grids while not requiring those public storage providers to maintain additional infrastructure (e.g., in the form of a backend `magic-wormhole` client that continuously dispenses new invite codes to end users).


How do "cheat codes" work?
--------------------------

"Cheat codes" work by embedding connection information for known/public storage providers directly into the Gridsync client -- specifically, in the form of JSON files located in the `gridsync/resources/providers` directory. Whenever an end user enters a "`0`"-prefixed invite code into their Gridsync client, Gridsync will check the aforementioned directory for any JSON files whose filename matches the tail of that invite code and load/process the assosiated JSON file as though it were received through a magic-wormhole.

Suppose, for example, that there exists a JSON file named "`storage-club.json`" in the `gridsync/resources/providers` directory whose contents contain the following:

```json
{
    "nickname": "Storage Club",
    "introducer": "pb://3kzbib7v5i6gmtd2vkjujfywqiwzintw@example.org:55555/2qdq3buyzmwq6xuxl4sdzyej5vswhkqs",
    "shares-needed": "1",
    "shares-happy": "1",
    "shares-total": "1"
}

```

Any end user wishing to join the "Storage Club" grid, then, can do so by simply entering an invite code of "`0-storage-club`" when prompted (e.g., by the initial Gridsync welcome dialog): Gridsync will automatically configure a new Tahoe-LAFS client with the settings provided above -- i.e., without requiring any additional action on behalf of the end user or the operators of the "Storage Club" service.


What "cheat codes" are available in Gridsync?
---------------------------------------------

Currently, no "cheat codes" are available in Gridsync -- but this may change in the future.. If you are a public storage provider and would like your grid's connection settings to be available for all users of Gridsync, please open a pull request with your grid's connection settings as described above (i.e., by adding the appropriate JSON file to the `gridsync/resources/providers` directory). For an example of keys/values that are acceptable for a grid connection, see [`docs/example-invite.json`](https://github.com/gridsync/gridsync/blob/master/docs/example-invite.json).
