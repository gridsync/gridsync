A proposal for Tahoe-LAFS intergrid "news" broadcasts
=====================================================
Christopher R. Wood <chris@leastauthority.com>

Problem:
--------

Presently, the operators of storage grid infrastructure have no standardized
means for securely communicating messages to the users of that infrastructure.
News or other information regarding server-side upgrades or scheduled downtime
that might disrupt service, for example, must be conveyed through other
commonly-used channels like email lists or a traditional webpage/feed. 
Unfortunately, these approaches typically have drawbacks which, arguably, 
jeopardize or diminish the expectations of privacy that users of Tahoe-LAFS 
would normally enjoy (or, privacy-concerns aside, otherwise demand additional 
labor on the part of both operators and users that may be seen as cumbersome): 
mailing lists, for example, require that the grid operator maintain a list of 
durable user-intenties, disclose the contents of messages to email providers,
and so on, while a traditional webpage/feed typically requires that users 
actively check a given URL, disclosing additional potentially personally-
identifiable information along the way (e.g., via browser metadata leaks to
the server, Google's "Safe Browsing" spyware, etc.).

Accordingly, it would be useful to both grid operators and users to be able to
leverage Tahoe-LAFS' existing privacy, security, and reliability guarantees to
establish a communication channel through which periodic messages could be 
delivered from operators to users. Ideally, this channel would both function 
entirely "in-band" (i.e., not require the user to depend on another application
or service for delivery) and be no more cumbersome or difficult to use than 
existing solutions.


A (possible) solution: "Newscaps":
-----------------------------------

Despite it's underlying "peer-to-peer" capabilities, in practice, a typical
deployment of a Tahoe-LAFS "storage grid" is one in which some singular party
("the operator") maintains an introducer node through to which users/clients 
initially connect and/or a majority of the storage nodes which comprise the 
"grid". In the case of Least Authority's commercial "Simple Secure Storage 
Service" ("S4"), users additionally depend upon the operator to determine and 
provide other connection-related information (such as the grid name, 
identifying icon/logo, and recommended erasure-coding parameters) to be written
directly directly to the user's `tahoe.cfg` file -- in this case, received 
through a secure "magic-wormhole" connection mediated by the user's 
agent/client via an "invite code" received shortly after sign-up. As such, 
users already typically expect to configure their local tahoe client with 
credentials/settings provided by the operator, while mechanisms already exist 
for establishing a secure a secure communication channel through which said 
credentials/settings can be safely delivered. 

Given the above, it would be useful if existent expectations and mechanisms 
could be extended in a way that would allow operators to maintain a secure 
communication channel to users long after the initial setup proceedure has been
completed but, crucially, without any other sacrifices to the user's security 
or privacy and without demanding any additional labor on behalf of the user. 
One way to do this would be for the operator to deliver to the user an 
additional "newscap" to the user alongside any other credentials/settings which
the user's agent/client could periodically read from in order to receive 
messages.

The "newscap" would consist in an ordinary Tahoe-LAFS directory capability 
("dircap") into which individual "mesages" would be linked, perhaps like so:

`$newscap`/2017-09-25T17:56:35.484632.txt`
`$newscap`/2017-10-13T13:22:03.782314.txt`
`$newscap`/2017-10-19T18:42:23.152504.txt`

(Note that naming the message files according to the timestamp is not really 
necessary since Tahoe-LAFS dircaps already preserve a `linkmotime` value in the
dircap's metadata; any filename could be used here)

Distinguishing between the top-level dircap and its underlying individual
messages (rather than structuring the "newscap" instead, say, as a single 
mutable writecap into which new messages are appended) would allow for the 
operator to remove old entries as desired while allowing the user's 
agent/client to more easily distinguish between messages that have already been
downloaded/seen and those that have not. In addition, this allows format users
of the Tahoe-LAFS CLI to more easily see when a new message has been added.

Naturally, only the operator would be in possession of the read/write 
capability needed to add entries to the newscap (and is thus the only party who
can "pushish" news/updates) while the user(s) would receive the "diminished" 
read-only capability (and thus be able to view/read -- but not modify -- the 
contents of messages). All users of the storage grid would presumably 
receive/store the same (read-only) "newscap" when initially configuring their
Tahoe-LAFS client.


Delivering the (read-only) "newscap":
-------------------------------------

As mentioned above, "newscaps" could be delivered to the user as a part of the
ordinary Tahoe-LAFS client configuration processs. For example, in the case of 
a user receiving Tahoe-LAFS credentials/settings via magic-wormhole (as in the
case of Least Authority's "S4"), the "newscap" might be simply be provided 
inside an additional "newscap" key/value field inside the standard 
magic-wormhole JSON message, like so:

```
{
    "nickname": "Bob's Storage Company",
    "shares-needed": "3",
    "shares-happy": "7",
    "shares-total": "10",
    "introducer": "pb://nywv4fj263fsimnkaeobhhwqkwcao5yz@bobs-storage.co:5000/ab3mxhglqgcdced6rxo27a4uh2qsz2wu",
    "newscap": "URI:DIR2-RO:b35hgnqozue43pr7fey2p6ughu:kkg2ipv5mlzweigr7b3xozuowqrkfpig5ovakvcflmct43cm6zcq"
}
```

Upon seeing such a "newscap", the user's Tahoe-LAFS agent could then store the 
value in the corresponding nodedir's "private" subdirectory (e.g., `Bob's 
Storage Company/private/newscap`) and make any backups of this capability as 
needed (for example, the Gridsync application <http://gridsync.io> might ensure
that this value is also accessible from the user's "rootcap" so that future 
news messages can be viewed in the event of a clean restore).


Publishing a message to the "newscap":
--------------------------------------

Because the "newscap" is, in actuality, an ordinary Tahoe-LAFS directory 
object, publishing a new message to it simply consists in uploading that 
message to the storage grid and linking the resultant capability into the 
(root) of the newscap. With the Tahoe-LAFS CLI, this can be done with the 
following command (assuming that the operator has already added a "newscap" 
alias pointing to its writecap):

`tahoe put /path/to/news.txt newscap:2017-10-19T18:42:23.152504.txt`


Reading the "newscap":
----------------------

As mentioned above, retrieving news "updates" is simply a matter of listing
the contents of that directory (e.g., using `tahoe ls $newscap`) and 
downloading/reading any linked files/messages that have not been viewed 
previously (e.g., using `tahoe get $newscap/2017-10-19T18:42:23.152504.txt`). 
In the case of a graphical Tahoe-LAFS agent application like Gridsync, the 
application might query the "newscap" on a regular -- or, to help combat 
behavioral profiling, a semi-regular -- basis on behalf of the user and 
display any new messages to the user (e.g., in the form of a messagebox/alert 
or desktop notification) as they are received. Additional interfaces, of 
course, could be added to help manage these messages as desired (e.g., to 
browse or delete old messages, to configure the frequency/regularity of 
update-checks, to disable the alerts altogether, etc.).


Other use-cases:
----------------

Although this document refers to the functionality described herein as 
"newscaps" and is intended primarily as a mechanism through which grid 
operators can deliver human-readable messages directly to _human_ users, the 
same or a similar mechanism could also be used to deliver messages that are 
intended primarily to be machine-readable or to be used by the user's 
agent/client in some other way. For example, a grid operator who provisions 
new -- or decommissions old -- storage servers on the grid might want to 
deliver a new list of storage fURLs to the users' agents/clients, allowing 
those users to make use of the new servers without the need to manually 
reconfigure their tahoe client(s) (though, of course, any such modifications 
should still require _consent_ from the user(s)).

Importantly, previous discussions pertaining to "newscap"-like features within
Least Authority in the context of S4 (circa 2017) have concluded that such a 
proposed feature should _not_ be used to deliver executable software updates
to users. Reasons considered centered primarily on concerns stemming from 
collapsing the separation of authority between "grid operators" on the one 
hand and "software developers" on the other: Although it is true that Least 
Authority both provides a commercial Tahoe-LAFS service _and_ employs most 
currently-active Tahoe-LAFS developers, Tahoe-LAFS' security model is 
explicitly predicated on the notion that users need not "trust" or depend upon
the storage service provider to preserve the confidentiality or integrity of
user-data. Accordingly, it is highly desirable that users be able and 
encouraged to independently download, verify, and use client software from 
persons who are _not_ identical to the operator of the storage grid to which
they are connecting. 


Security considerations:
------------------------

It should go without saying that the possessor of the newscap's read/write 
capability ("writecap") must take extra precautions to ensure that the 
capability remains confidential. While possessing the newscap's write 
capability would not allow an attacker to, e.g., read existing user data, its 
possession could nevertheless be abused in any number of ways that could lead 
to such circumstances (e.g., by sending out a message containing a link to 
malware disguised as a "software update" that might exfiltrate's the user's 
rootcap). Keeping in mind, further, Tahoe-LAFS' overarching security model 
(e.g., that storage _servers_ need not be "trusted" to provide any property 
other than ciphertext availability), good practices would suggest that the 
writecap should not be stored/used on any machines that might constitute grid 
"infrastucture" either or any other obvious attack vectors (including, most 
obviously, the storage nodes themselves). Accordingly, the author recommends 
keeping the writecap stored securely on dedicated hardware and be brought 
online and used only as needed.
