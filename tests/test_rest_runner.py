import json
from pathlib import Path
from typing import Optional
from unittest import TestCase

from httmock import HTTMock, all_requests, response

from rasa_integration_testing.common.configuration import (
    Configuration,
    DependencyInjector,
)
from rasa_integration_testing.comparator import JsonPath
from rasa_integration_testing.interaction import INTERACTION_TURN_EXTENSION
from rasa_integration_testing.rest_runner import (
    SENDER_ID_KEY,
    RestProtocolException,
    RestRunner,
)
from rasa_integration_testing.runner import FailedInteraction
from rasa_integration_testing.scenario import Scenario

YML_EXTENSION = "yml"
INI_EXTENSION = "ini"

TEST_DEFINITIONS_FOLDER = Path("tests/main_scenarios/")
SUCCESS_TESTS_PATH = TEST_DEFINITIONS_FOLDER / "success"
FRAGMENTED_TESTS_PATH = TEST_DEFINITIONS_FOLDER / "fragmented"
INTERACTION_TEMPLATES_TESTS_PATH = TEST_DEFINITIONS_FOLDER / "interaction_templates"
FAILURE_TESTS_PATH = TEST_DEFINITIONS_FOLDER / "fail"

SUCCESS_SCENARIO_PATH = SUCCESS_TESTS_PATH / f"scenarios/success.{YML_EXTENSION}"
FRAGMENTED_SCENARIO_PATH = (
    FRAGMENTED_TESTS_PATH / f"scenarios/fragmented.{YML_EXTENSION}"
)
INTERACTION_TEMPLATES_SCENARIO_PATH = (
    INTERACTION_TEMPLATES_TESTS_PATH
    / f"scenarios/interaction_templates.{YML_EXTENSION}"
)
FAILURE_SCENARIO_PATH = FAILURE_TESTS_PATH / f"scenarios/fail.{YML_EXTENSION}"

WELCOME_JSON_DATA = (
    TEST_DEFINITIONS_FOLDER
    / f"fail/interactions/bot/welcome.{INTERACTION_TURN_EXTENSION}"
)
INITIAL_INVALID_DATA = (
    TEST_DEFINITIONS_FOLDER
    / f"fail/interactions/user/initial_invalid.{INTERACTION_TURN_EXTENSION}"
)


class TestRunner(TestCase):
    def test_identical(self):
        with HTTMock(request_response):
            runner = _scenario_runner(SUCCESS_TESTS_PATH)
            result = runner.run(Scenario.from_file("success", SUCCESS_SCENARIO_PATH))
            self.assertEqual(result, None)

    def test_fragmented(self):
        with HTTMock(request_response):
            runner = _scenario_runner(FRAGMENTED_TESTS_PATH)
            result = runner.run(
                Scenario.from_file("fragmented", FRAGMENTED_SCENARIO_PATH)
            )
            self.assertEqual(result, None)

    def test_interaction_templates(self):
        with HTTMock(request_response):
            runner = _scenario_runner(INTERACTION_TEMPLATES_TESTS_PATH)
            result = runner.run(
                Scenario.from_file(
                    "interaction_templates", INTERACTION_TEMPLATES_SCENARIO_PATH
                )
            )
            self.assertEqual(result, None)

    def test_not_identical(self):
        with HTTMock(request_response):
            runner = _scenario_runner(FAILURE_TESTS_PATH)

            result: Optional[FailedInteraction] = runner.run(
                Scenario.from_file("failure", FAILURE_SCENARIO_PATH)
            )
            self.assertIsNotNone(result)
            self.assertEqual(
                json.load(open(WELCOME_JSON_DATA, "r")), result.expected_output
            )
            self.assertEqual(
                result.output_diff.missing_entries,
                {JsonPath("messages", "_1", "synthesis"): "Welcome to NuBank!"},
            )
            actual_output = result.actual_output
            actual_output.pop(SENDER_ID_KEY)
            self.assertEqual({}, actual_output)


class TestRunnerProtocolException(TestCase):
    def test_protocol_exception(self):
        with HTTMock(text_response):
            with self.assertRaises(RestProtocolException):
                runner = _scenario_runner(SUCCESS_TESTS_PATH)
                runner.run(Scenario.from_file("success", SUCCESS_SCENARIO_PATH))


def _scenario_runner(tests_path: Path) -> RestRunner:
    return DependencyInjector(
        Configuration(tests_path / f"config.{INI_EXTENSION}"),
        {"tests_path": tests_path},
    ).autowire(RestRunner)


@all_requests
def text_response(url, request):
    headers = {"content-type": "text/plain"}
    content = "This should fail"
    return response(200, content, headers, None, 5, request)


@all_requests
def request_response(url, request):
    headers = {"content-type": "application/json"}
    return response(200, request.body, headers, None, 5, request)
