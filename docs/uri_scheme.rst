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

st, n, N = shares.total

sn, k, K = shares.needed

sh, h, H = shares.happy

D = Directory writecap
d = Directory readcap
F = 


SDMF directory:

Directory writecap  URI:DIR2:ms57fyg3vqugkw5bn7hvhg3d5i:lva25fevt7vohlty2otjaglqfeghww3l3dtiw56a7uoxlupuqn7q
Directory readcap   URI:DIR2-RO:jaqtgpmlqhorhifozyunpypfha:lva25fevt7vohlty2otjaglqfeghww3l3dtiw56a7uoxlupuqn7q
Directory verifycap URI:DIR2-Verifier:estskhs3tmkgzuymwgn6vpsmrq:lva25fevt7vohlty2otjaglqfeghww3l3dtiw56a7uoxlupuqn7q
File writecap       URI:SSK:ms57fyg3vqugkw5bn7hvhg3d5i:lva25fevt7vohlty2otjaglqfeghww3l3dtiw56a7uoxlupuqn7q
File readcap        URI:SSK-RO:jaqtgpmlqhorhifozyunpypfha:lva25fevt7vohlty2otjaglqfeghww3l3dtiw56a7uoxlupuqn7q
File verifycap      URI:SSK-Verifier:estskhs3tmkgzuymwgn6vpsmrq:lva25fevt7vohlty2otjaglqfeghww3l3dtiw56a7uoxlupuqn7q


MDMF (experimental) directory:

Directory writecap  URI:DIR2-MDMF:d527jorfm6agcciob3inovpz6m:4ypc7pwo7tpyedtdus3coee2qdroettvohwf5zo4g472bfxbeqya
Directory readcap   URI:DIR2-MDMF-RO:t7ogprkqah3ti3qjwliaiatvay:4ypc7pwo7tpyedtdus3coee2qdroettvohwf5zo4g472bfxbeqya
Directory verifycap URI:DIR2-MDMF-Verifier:ssqou2trhz2jwtngvys4zfn6vm:4ypc7pwo7tpyedtdus3coee2qdroettvohwf5zo4g472bfxbeqya
File writecap       URI:MDMF:d527jorfm6agcciob3inovpz6m:4ypc7pwo7tpyedtdus3coee2qdroettvohwf5zo4g472bfxbeqya
File readcap        URI:MDMF-RO:t7ogprkqah3ti3qjwliaiatvay:4ypc7pwo7tpyedtdus3coee2qdroettvohwf5zo4g472bfxbeqya
File verifycap      URI:MDMF-Verifier:ssqou2trhz2jwtngvys4zfn6vm:4ypc7pwo7tpyedtdus3coee2qdroettvohwf5zo4g472bfxbeqya


Immutable file

1-URI:CHK:2fl2eb2b6qjk5n34gcwemd4xmy:wkca4gj5xsdls5dhkjr6lcphuil3qs5igzfrmpongw7ufsw6jwxq:2:6:285136


SDMF file

URI:SSK:tfxsdyyvdtwqlmlyfka6iqv32e:7kkri2dua65g2lomssdi2c5xpz3gl5dpbrpltd374eqtdrjjveza

MDMF (experimental)

URI:MDMF:idcn2u6kjqqrp3ufw5ktfslsh4:iegj2n6jgfn4t7j2iexu3ltqxojasd6bqnmxgbv5qn5bsxkhdhkq












Examples
--------

``gridsync://cwrh3t4vselhmcrdzt65rgxlcw5s3zaz@example.org:46210``

Client prompts user to either a) "use this grid for storage" or b) "share storage space with this grid"

``gridsync://cwrh3t4vselhmcrdzt65rgxlcw5s3zaz@example.org:46210/DIR2:ud4yxj5zmyyxr2ue23u3kuzjwu:qc6inqijwur7xmhmovh7iovwmwykok6ibtefkpbhbe2inktytnma?d=My+Documents``

Client creates a new Tahoe-LAFS node with name "My Documents", configures it to connect to the introducer at example.org, starts node, prompts user for a save location, and sets up a sync-pipe between that save location and the cap specified

``gridsync:?s=127.0.0.1:5678,192.168.1.1:6789``

Client prompts to create a new introducerless grid with 127.0.0.1:5678 and 192.168.1.1:6789 or to add 127.0.0.1:5678 and 192.168.1.1:6789 to an existing introducerless grid
