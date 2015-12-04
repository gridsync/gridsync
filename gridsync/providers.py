# -*- coding: utf-8 -*-


PROVIDERS = {
    'Tahoe-LAFS Public Test Grid': {
        'introducer.furl': "pb://hckqqn4vq5ggzuukfztpuu4wykwefa6d@publictestgrid.twilightparadox.com:50213,publictestgrid.lukas-pirl.de:50213,publictestgrid.e271.net:50213,198.186.193.74:50213,68.34.102.231:50213/introducer",
        'description': "A public storage grid run by members of the Tahoe-LAFS community. This storage grid is inteded to be used primarily for testing purposes and makes no guarantees with regard to availability; don't store any data in the pubgrid if losing it would cause trouble.",
        'homepage': "https://tahoe-lafs.org/trac/tahoe-lafs/wiki/TestGrid"
    }
    'test.gridsync.io': {
        'introducer.furl': "pb://3kzbib3v5i7gmtd2vkjujfywqiwzintw@test.gridsync.io:44800/2qdq2buyzmwq6xuxl2sdzyej5vswhkqs",
        'description': "A test grid maintained by the developer(s) of Gridsync. Part of the Gridsync testing infrastructure, this storage grid has high availability but very low capacity; use this for testing purposes only as its shares will be flushed every 72 hours."
        'homepage': "https://test.gridsync.io"
    }
}
