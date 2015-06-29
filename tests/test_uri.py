from gridsync.uri import *

i = "gridsync://cmrh4t4vselhwcrdzt56rgxlcw5s2zaz@162.243.228.43:46210/DIR2:ud4yxj5zmyyxr2ue23u3kuzjwu:qc6inqijwur7xmhmovh7iovwmwykok6ibtefkpbhbe2inktytnma?n=test"

def test_remove_prefix():
    assert remove_prefix("gridsync://blah") == "blah"


