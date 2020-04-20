import asyncio
import json
from pathlib import Path
from typing import Any, Optional
from unittest import TestCase

from aiohttp import ClientSession

from integration_testing.comparator import JsonDataComparator, JsonPath
from integration_testing.configuration import Configuration, DependencyInjector
from integration_testing.interaction import (
    INTERACTION_TURN_EXTENSION,
    InteractionLoader,
)
from integration_testing.protocol import ProtocolException, protocol_selector
from integration_testing.runner import SENDER_ID_KEY, FailedInteraction, ScenarioRunner
from integration_testing.scenario import Scenario, ScenarioFragmentLoader

YML_EXTENSION = "yml"
INI_EXTENSION = "ini"

TEST_DEFINITIONS_FOLDER = Path("tests/main_scenarios/")
SUCCESS_TESTS_PATH = TEST_DEFINITIONS_FOLDER.joinpath(f"success")
FRAGMENTED_TESTS_PATH = TEST_DEFINITIONS_FOLDER.joinpath(f"fragmented")
INTERACTION_TEMPLATES_TESTS_PATH = TEST_DEFINITIONS_FOLDER.joinpath(
    f"interaction_templates"
)
FAILURE_TESTS_PATH = TEST_DEFINITIONS_FOLDER.joinpath(f"fail")

SUCCESS_SCENARIO_PATH = TEST_DEFINITIONS_FOLDER.joinpath(
    f"success/scenarios/success.{YML_EXTENSION}"
)
FRAGMENTED_SCENARIO_PATH = TEST_DEFINITIONS_FOLDER.joinpath(
    f"fragmented/scenarios/fragmented.{YML_EXTENSION}"
)
INTERACTION_TEMPLATES_SCENARIO_PATH = TEST_DEFINITIONS_FOLDER.joinpath(
    f"interaction_templates/scenarios/interaction_templates.{YML_EXTENSION}"
)
FAILURE_SCENARIO_PATH = TEST_DEFINITIONS_FOLDER.joinpath(
    f"fail/scenarios/fail.{YML_EXTENSION}"
)

WELCOME_JSON_DATA = TEST_DEFINITIONS_FOLDER.joinpath(
    f"fail/interactions/bot/welcome.{INTERACTION_TURN_EXTENSION}"
)
INITIAL_INVALID_DATA = TEST_DEFINITIONS_FOLDER.joinpath(
    f"fail/interactions/user/initial_invalid.{INTERACTION_TURN_EXTENSION}"
)


class TestRunner(TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_identical(self):
        injector = _injector(SUCCESS_TESTS_PATH)
        runner = ScenarioRunner(
            injector.autowire(protocol_selector),
            InteractionLoader(SUCCESS_TESTS_PATH),
            ScenarioFragmentLoader(SUCCESS_TESTS_PATH),
            injector.autowire(JsonDataComparator),
        )
        result = self._sync_run(
            runner, Scenario.from_file("success", SUCCESS_SCENARIO_PATH)
        )
        self.assertEqual(result, None)

    def test_fragmented(self):
        injector = _injector(FRAGMENTED_TESTS_PATH)
        runner = ScenarioRunner(
            injector.autowire(protocol_selector),
            InteractionLoader(FRAGMENTED_TESTS_PATH),
            ScenarioFragmentLoader(FRAGMENTED_TESTS_PATH),
            injector.autowire(JsonDataComparator),
        )
        result = self._sync_run(
            runner, Scenario.from_file("fragmented", FRAGMENTED_SCENARIO_PATH)
        )
        self.assertEqual(result, None)

    def test_interaction_templates(self):
        injector = _injector(INTERACTION_TEMPLATES_TESTS_PATH)
        runner = ScenarioRunner(
            injector.autowire(protocol_selector),
            InteractionLoader(INTERACTION_TEMPLATES_TESTS_PATH),
            ScenarioFragmentLoader(INTERACTION_TEMPLATES_TESTS_PATH),
            injector.autowire(JsonDataComparator),
        )
        result = self._sync_run(
            runner,
            Scenario.from_file(
                "interaction_templates", INTERACTION_TEMPLATES_SCENARIO_PATH
            ),
        )
        self.assertEqual(result, None)

    def test_not_identical(self):
        injector = _injector(FAILURE_TESTS_PATH)
        runner = ScenarioRunner(
            injector.autowire(protocol_selector),
            InteractionLoader(FAILURE_TESTS_PATH),
            ScenarioFragmentLoader(FAILURE_TESTS_PATH),
            injector.autowire(JsonDataComparator),
        )

        result: Optional[FailedInteraction] = self._sync_run(
            runner, Scenario.from_file("failure", FAILURE_SCENARIO_PATH)
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

    def test_protocol_exception(self):
        with self.assertRaises(ProtocolException):
            injector = _injector(SUCCESS_TESTS_PATH)
            runner = ScenarioRunner(
                injector.autowire(protocol_selector),
                InteractionLoader(SUCCESS_TESTS_PATH),
                ScenarioFragmentLoader(SUCCESS_TESTS_PATH),
                injector.autowire(JsonDataComparator),
            )
            self._sync_run(
                runner, Scenario.from_file("success", SUCCESS_SCENARIO_PATH), True
            )

    def _sync_run(
        self, runner: ScenarioRunner, scenario: Scenario, fake_session: bool = False
    ) -> Any:
        session = asyncio.new_event_loop().run_until_complete(
            _create_client_session(fake_session)
        )
        return asyncio.new_event_loop().run_until_complete(
            runner.run(scenario, session)
        )


async def _create_client_session(fake_session: bool):
    return ClientSession() if not fake_session else None


def _injector(tests_path: Path) -> DependencyInjector:
    return DependencyInjector(Configuration(tests_path.joinpath("config.ini")))
