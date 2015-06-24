import unittest

import gridsync.uri


class UriTest(unittest.TestCase):
    def test_remove_prefix(self):
        self.assertEqual(gridsync.uri.remove_prefix("gridsync://blah"), "blah")

