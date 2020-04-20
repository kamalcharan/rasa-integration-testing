from unittest import TestCase

from rasa_integration_testing.common import quick_chunk


class TestCommon(TestCase):
    def test_quick_chunk(self):
        chunks = quick_chunk(("a", "b", "c"), 2)
        self.assertEqual(tuple(chunks), (("a", "b"), ("c", None)))

    def test_quick_chunk_under_chunk_size(self):
        chunks = quick_chunk(("a"), 3)
        self.assertEqual(tuple(chunks), (("a", None, None),))
