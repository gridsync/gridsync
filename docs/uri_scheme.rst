===================
Gridsync URI Scheme
===================

The Gridsync URI scheme is intended to facilitate the sharing of resources between users. By installing a URI-handler at the system level during the first run procedure, ``gridsync:`` links clicked by a user in other applications (e.g., in an XMPP conversation) can be passed directly to the Gridsync client, effectively eliminating the need to manually type or paste configuration details into the client. In effect, this allows a user to join another user's storage grid via a simple series of clicks or to accept a Tahoe-LAFS Magic Folder invite without having previously connected to the grid in which it is stored.

Since the exposure of a Gridsync URI effectively discloses the details necessary to access a resource, extra care should be taken to ensure that they are not disclosed indiscriminately; users should be encouraged to share such links through authenticated and secure and channels only and warned (e.g., through confirmation dialogs) of the potential conequences of accepting such links from unknown parties.


Generic syntax
--------------

Two formats -- hierarchical and non-hierarchical -- are available and should be considered valid:

``gridsync://<introducer_tub_id>@<introducer_location_hints>/<introducer_name>/<dircap>[+<magic_folder_client_writecap]>``

``gridsync:?<key>=<value>[?<key>=<value>]``


Valid queries
-------------

The following queries (in format ``?<key>=<value>``) should be accepted as valid. Queries may be declared in any order and any number of times (making it possible, for example, to specify several storage fURLs in order to share access an introducerless grid):

``i`` = introducer fURL (sans ``pb://`` prefix)

``s`` = storage fURL (sans ``pb://`` prefix)

``d`` = dircap (``URI:`` prefix optional)

``mf`` = Magic Folder invite code (presently in format ``collective_readcap+client_writecap``)


Examples
--------

``gridsync://cwrh3t4vselhmcrdzt65rgxlcw5s3zaz@example.org:46210/introducer``

An introducer fURL hosted at example.org. When implemented, clicking this URI will prompt the user to add an "example.org" grid to their list of known storage providers, making it available for future use.


``gridsync://cwrh3t4vselhmcrdzt65rgxlcw5s3zaz@example.org:46210/introducer/DIR2-RO:jaqtgpmlqhorhifozyunpypfha:lva25fevt7vohlty2otjaglqfeghww3l3dtiw56a7uoxlupuqn7q``

A read-only directory accessible via storage nodes using the introducer at example.org. Clicking this URI will prompt the user to select a local directory into which the remote contents will be downloaded. If necessary, "example.org" will be added to the list of known storage providers and a newly configured Tahoe-LAFS gateway will be launched through which the contents will downloaded. 


``gridsync://cwrh3t4vselhmcrdzt65rgxlcw5s3zaz@example.org:46210/introducer/URI:DIR2-RO:mz2evrnpry4ip2wqktiut4tv7u:yot5uei6qhvjvuyw4hqudhlyqwnafvzmv4nwk3l53kfvch6rnapa+URI:DIR2:6zkejlgjbalmezwa4kkverms2a:t2ybdbllchplttvyyn3xcygvnnvl6em7pujtsn2ll6vyvquadpya``

An invitation to join a Magic Folder. Similar to the example above, clicking this URI will prompt the user for a local directory and, if needed, launch a new Tahoe-LAFS gateway.


``gridsync:?s=b52hkg3qy6fuxuvw3dzno3tiv2gxo65a@node1.example.org:46592/wpsagzgxfh6crdccbdzsmdlrgd22lfdb?s=vpupqs3njjbei2roq3uosfn7ieohi33m@node2.example.org:43874/4kgxh4ejsr4oguy6pxjlxw2ltyjjbcco``

Two storage fURLs comprising an introducerless grid.


``gridsync:?s=b52hkg3qy6fuxuvw3dzno3tiv2gxo65a@node1.example.org:46592/wpsagzgxfh6crdccbdzsmdlrgd22lfdb?s=vpupqs3njjbei2roq3uosfn7ieohi33m@node2.example.org:43874/4kgxh4ejsr4oguy6pxjlxw2ltyjjbcco?mf=URI:DIR2-RO:h7xqv4e3qjvim72sher5g27ddu:z3t6csgg3icahqro5p7abkqql6t25ly3cfqm3zhtyprrmbtfgiva+URI:DIR2:w2mpnzcprfvjrlngav7xyr5nia:ksbgb6h565txmlezx4prvhabqjzekoiiumlemeyoqsip3d6ddj4a``

An invitation to join a Magic Folder on an introducerless grid.


Concerns
--------

Taken together, Tahoe-LAFS fURLs and capabilities are especially long which could result in UX-related issues in certain contexts (e.g., with message-length limitations or line-wrapping). It may be worth considering ways to shorten URI lengths through some other means (e.g., by using a hash of the string instead, storing the full string encrypted in a distributed database or hash table) while recognizing the need to strike an appropriate balance between security and convenience. See also Tahoe-LAFS "GridID" proposal document: https://github.com/tahoe-lafs/tahoe-lafs/blob/master/docs/proposed/GridID.txt
