import asyncio
import json
from pathlib import Path
from typing import Optional
from unittest import TestCase

from aiohttp import web
from aiohttp.test_utils import Request, TestServer

from rasa_integration_testing.common.configuration import (
    Configuration,
    DependencyInjector,
)
from rasa_integration_testing.comparator import JsonPath
from rasa_integration_testing.interaction import INTERACTION_TURN_EXTENSION
from rasa_integration_testing.rest_runner import (
    SENDER_ID_KEY,
    RestProtocolException,
    RestScenarioRunner,
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
    def setUp(self):
        async def return_user_input(request: Request):
            json_dict = await request.json()
            return web.Response(
                body=json.dumps(json_dict), content_type="application/json"
            )

        app = web.Application()
        app.router.add_post("/", return_user_input)
        self.server = TestServer(app, port=8080)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.server.start_server())

    def tearDown(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.run())
        loop.run_until_complete(self.server.close())

    def test_identical(self):
        async def run():
            runner = _scenario_runner(SUCCESS_TESTS_PATH)
            result = await runner.run(
                Scenario.from_file("success", SUCCESS_SCENARIO_PATH)
            )
            self.assertEqual(result, None)

        self.run = run

    def test_fragmented(self):
        async def run():
            runner = _scenario_runner(FRAGMENTED_TESTS_PATH)
            result = await runner.run(
                Scenario.from_file("fragmented", FRAGMENTED_SCENARIO_PATH)
            )
            self.assertEqual(result, None)

        self.run = run

    def test_interaction_templates(self):
        async def run():
            runner = _scenario_runner(INTERACTION_TEMPLATES_TESTS_PATH)
            result = await runner.run(
                Scenario.from_file(
                    "interaction_templates", INTERACTION_TEMPLATES_SCENARIO_PATH
                )
            )
            self.assertEqual(result, None)

        self.run = run

    def test_not_identical(self):
        async def run():
            runner = _scenario_runner(FAILURE_TESTS_PATH)

            result: Optional[FailedInteraction] = await runner.run(
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

        self.run = run


class TestRunnerProtocolException(TestCase):
    def setUp(self):
        async def return_user_input(request: Request):
            return web.Response(content_type="text/plain")

        app = web.Application()
        app.router.add_post("/", return_user_input)
        self.server = TestServer(app, port=8080)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.server.start_server())

    def tearDown(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.run())
        loop.run_until_complete(self.server.close())

    def test_protocol_exception(self):
        async def run():
            with self.assertRaises(RestProtocolException):
                runner = _scenario_runner(SUCCESS_TESTS_PATH)
                await runner.run(Scenario.from_file("success", SUCCESS_SCENARIO_PATH))

        self.run = run


def _scenario_runner(tests_path: Path) -> RestScenarioRunner:
    return DependencyInjector(
        Configuration(tests_path / f"config.{INI_EXTENSION}"),
        {"tests_path": tests_path},
    ).autowire(RestScenarioRunner)
