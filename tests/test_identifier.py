from unittest import TestCase

from integration_testing.identifier import Identifier

ELEMENTS = ["en-US", "pay_bill", "initial"]


class TestIdentifier(TestCase):
    def test_equals(self):
        self.assertEqual(Identifier(*ELEMENTS), Identifier(*ELEMENTS))

    def test_length(self):
        self.assertEqual(len(Identifier(*ELEMENTS)), 3)

    def test_string(self):
        self.assertEqual(str(Identifier(*ELEMENTS)), "en-US.pay_bill.initial")

    def test_add(self):
        identifier = Identifier(*ELEMENTS) + ["another"]
        self.assertEqual(str(identifier), "en-US.pay_bill.initial.another")
