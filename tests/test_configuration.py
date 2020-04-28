from pathlib import Path
from typing import Callable
from unittest import TestCase

from rasa_integration_testing.configuration import (
    Configuration,
    DependencyInjector,
    configure,
)


@configure(extra="keyword")
class ExtraKeywordArgument:
    def __init__(self):
        pass


@configure("extra.argument")
class ExtraArgument:
    def __init__(self):
        pass


class NonConfiguredObject:
    def __init__(self):
        pass


@configure("section.text", "section.flag", "section.number", "section.floating_number")
class ConfiguredObject:
    def __init__(self, text: str, flag: bool, number: int, fnumber: float):
        self.text = text
        self.flag = flag
        self.number = number
        self.fnumber = fnumber


@configure("section.text", flag="section.flag", number="section.number")
class MixedParameters:
    def __init__(self, text: str, number: int, flag: bool):
        self.text = text
        self.number = number
        self.flag = flag


@configure(configured_object=ConfiguredObject, value=5)
class PassedValueObject:
    def __init__(self, configured_object: ConfiguredObject, value: int):
        self.configured_object = configured_object
        self.value = value


@configure("invalid_option")
class InvalidConfiguredObject:
    def __init__(self, option: str):
        self.option = option


INJECTOR = DependencyInjector(Configuration(Path("tests/config.ini")))


class TestConfiguration(TestCase):
    def test_valid_autowiring(self):
        configured_object: ConfiguredObject = INJECTOR.autowire(ConfiguredObject)
        self.assertEqual(configured_object.flag, True)
        self.assertEqual(configured_object.number, 4)
        self.assertEqual(configured_object.fnumber, 2.1)
        self.assertEqual(configured_object.text, "It works!")

    def test_passed_values(self):
        passed_value_object: PassedValueObject = INJECTOR.autowire(PassedValueObject)
        self.assertEqual(passed_value_object.value, 5)
        self.assertEqual(passed_value_object.configured_object.number, 4)

    def test_mixed_parameters(self):
        mixed_parameters: MixedParameters = INJECTOR.autowire(MixedParameters)
        self.assertEqual(mixed_parameters.number, 4)

    def test_invalid_autowiring(self):
        self._assert_error(
            "Invalid configure decorator option: invalid_option from"
            " InvalidConfiguredObject configure tag. Use the format section.option",
            InvalidConfiguredObject,
        )

    def test_normal_constructor(self):
        text = "The normal constructor works."
        invalid_object: InvalidConfiguredObject = InvalidConfiguredObject(text)
        self.assertEqual(invalid_object.option, text)

    def test_non_configured(self):
        self._assert_error(
            "Tried to autowire non-configured object NonConfiguredObject",
            NonConfiguredObject,
        )

    def test_extra_argument(self):
        self._assert_error(
            "ExtraArgument configure decorator has too many arguments", ExtraArgument
        )

    def test_extra_keyword_argument(self):
        self._assert_error(
            "ExtraKeywordArgument configure decorator got unexpected argument 'extra'",
            ExtraKeywordArgument,
        )

    def _assert_error(self, message: str, function: Callable):
        with self.assertRaises(Exception) as error:
            INJECTOR.autowire(function)
        self.assertEqual(f"{error.exception}", message)
