===================
Gridsync URI Scheme
===================

Generic syntax
--------------

``gridsync://<nodeid>@<introducer_address>:<introducer_port>/<cap>``


Valid queries
-------------


i = introducer (in format <key>@<address>:<port>) "pb://" prefix and "/introducer" suffix optional

s = storage server

c = Tahoe-LAFS cap, "URI:" prefix optional

d, f = directory- or file-name

st, n = shares.total

sn, k = shares.needed

sh, h = shares.happy


Examples
--------

``gridsync://cwrh3t4vselhmcrdzt65rgxlcw5s3zaz@example.org:46210``

Client prompts user to either a) "use this grid for storage" or b) "share storage space with this grid"

``gridsync://cwrh3t4vselhmcrdzt65rgxlcw5s3zaz@example.org:46210/DIR2:ud4yxj5zmyyxr2ue23u3kuzjwu:qc6inqijwur7xmhmovh7iovwmwykok6ibtefkpbhbe2inktytnma?d=My+Documents``

Client creates a new Tahoe-LAFS node with name "My Documents", configures it to connect to the introducer at example.org, starts node, prompts user for a save location, and sets up a sync-pipe between that save location and the cap specified

``gridsync:?s=127.0.0.1:5678,192.168.1.1:6789``

Client prompts to create a new introducerless grid with 127.0.0.1:5678 and 192.168.1.1:6789 or to add 127.0.0.1:5678 and 192.168.1.1:6789 to an existing introducerless grid
