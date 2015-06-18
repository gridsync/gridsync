import unittest

import gridsync.utils


class MyTest(unittest.TestCase):
    def test__utc_to_epoch(self):
        self.assertEqual(gridsync.utils.utc_to_epoch("2015-06-16_02:48:40Z"), 1434437320)

#if __name__ == '__main__':
#    unittest.main()
