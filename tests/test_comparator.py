from unittest import TestCase

from rasa_integration_testing.comparator import JsonDataComparator, JsonDiff, JsonPath


class TestComparator(TestCase):
    def setUp(self):
        self.comparator = JsonDataComparator("ignored.key,another")

    def test_compare_identical_empty(self):
        result: JsonDiff = self.comparator.compare({}, {})
        self.assertTrue(result.identical)

    def test_compare_identical_ignored(self):
        result: JsonDiff = self.comparator.compare(
            {"ignored": {"key": "this should be ignored"}}, {"another": "this also"}
        )
        self.assertTrue(result.identical)

    def test_compare_missing_key(self):
        result: JsonDiff = self.comparator.compare({"missing": [{"key": "value"}]}, {})
        self.assertFalse(result.identical)
        self.assertEqual(
            result.missing_entries, {JsonPath("missing", "_1", "key"): "value"}
        )

    def test_compare_extra_key(self):
        result: JsonDiff = self.comparator.compare({}, {"extra": "key"})
        self.assertFalse(result.identical)
        self.assertEqual(result.extra_entries, {JsonPath("extra"): "key"})

    def test_compare_unequal_value(self):
        key = "key"
        result: JsonDiff = self.comparator.compare({key: "value1"}, {key: "value2"})
        self.assertFalse(result.identical)
        path = JsonPath(key)
        self.assertEqual(result.missing_entries, {path: "value1"})
        self.assertEqual(result.extra_entries, {path: "value2"})

    def test_ignore_null_in_expected(self):
        value = "value"
        key = "key"
        path = JsonPath(key)

        result: JsonDiff = self.comparator.compare({key: None}, {key: value})
        self.assertTrue(result.identical)

        result: JsonDiff = self.comparator.compare({key: None}, {})
        self.assertTrue(result.identical)

        result: JsonDiff = self.comparator.compare({key: None}, {key: None})
        self.assertTrue(result.identical)

        result: JsonDiff = self.comparator.compare({key: value}, {key: None})
        self.assertFalse(result.identical)
        self.assertEqual(result.missing_entries, {path: value})
        self.assertEqual(result.extra_entries, {path: None})

        result: JsonDiff = self.comparator.compare({}, {key: None})
        self.assertFalse(result.identical)
        self.assertEqual(result.missing_entries, {})
        self.assertEqual(result.extra_entries, {path: None})

    def test_ignore_null_in_expected_deep(self):
        expected = {
            "A": {"A": "value", "B": None, "C": None},
        }

        actual = {
            "A": {"A": "value", "B": "value"},
        }

        result: JsonDiff = self.comparator.compare(expected, actual)
        self.assertTrue(result.identical)

    def test_ignore_null_only_on_leaf_keys(self):
        expected = {"A": None}
        actual = {"A": {"B": "value"}}
        path = JsonPath("A", "B")

        # We currently only support ignoring leaf keys
        result: JsonDiff = self.comparator.compare(expected, actual)
        self.assertFalse(result.identical)
        self.assertEqual(result.missing_entries, {})
        self.assertEqual(result.extra_entries, {path: "value"})
