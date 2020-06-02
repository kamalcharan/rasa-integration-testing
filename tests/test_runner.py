import json
from pathlib import Path
from typing import Optional

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, Request, unittest_run_loop

from rasa_integration_testing.common.configuration import (
    Configuration,
    DependencyInjector,
)
from rasa_integration_testing.comparator import JsonPath
from rasa_integration_testing.interaction import INTERACTION_TURN_EXTENSION
from rasa_integration_testing.protocol import ProtocolException
from rasa_integration_testing.runner import (
    SENDER_ID_KEY,
    FailedInteraction,
    ScenarioRunner,
)
from rasa_integration_testing.scenario import Scenario

YML_EXTENSION = "yml"
INI_EXTENSION = "ini"

TEST_DEFINITIONS_FOLDER = Path("tests/main_scenarios/")
SUCCESS_TESTS_PATH = TEST_DEFINITIONS_FOLDER / f"success"
FRAGMENTED_TESTS_PATH = TEST_DEFINITIONS_FOLDER / f"fragmented"
INTERACTION_TEMPLATES_TESTS_PATH = TEST_DEFINITIONS_FOLDER / f"interaction_templates"
FAILURE_TESTS_PATH = TEST_DEFINITIONS_FOLDER / f"fail"

SUCCESS_SCENARIO_PATH = (
    TEST_DEFINITIONS_FOLDER / f"success/scenarios/success.{YML_EXTENSION}"
)
FRAGMENTED_SCENARIO_PATH = (
    TEST_DEFINITIONS_FOLDER / f"fragmented/scenarios/fragmented.{YML_EXTENSION}"
)
INTERACTION_TEMPLATES_SCENARIO_PATH = (
    TEST_DEFINITIONS_FOLDER
    / f"interaction_templates/scenarios/interaction_templates.{YML_EXTENSION}"
)
FAILURE_SCENARIO_PATH = TEST_DEFINITIONS_FOLDER / f"fail/scenarios/fail.{YML_EXTENSION}"

WELCOME_JSON_DATA = (
    TEST_DEFINITIONS_FOLDER
    / f"fail/interactions/bot/welcome.{INTERACTION_TURN_EXTENSION}"
)
INITIAL_INVALID_DATA = (
    TEST_DEFINITIONS_FOLDER
    / f"fail/interactions/user/initial_invalid.{INTERACTION_TURN_EXTENSION}"
)


class TestRunner(AioHTTPTestCase):
    async def get_application(self):
        async def return_user_input(request: Request):
            json_dict = await request.json()
            return web.Response(
                body=json.dumps(json_dict), content_type="application/json"
            )

        app = web.Application()
        app.router.add_post("/", return_user_input)
        return app

    def setUp(self):
        super().setUp()
        self.maxDiff = None

    @unittest_run_loop
    async def test_identical(self):
        runner = _scenario_runner(SUCCESS_TESTS_PATH)
        result = await runner.run(
            Scenario.from_file("success", SUCCESS_SCENARIO_PATH), self.client
        )
        self.assertEqual(result, None)

    @unittest_run_loop
    async def test_fragmented(self):
        runner = _scenario_runner(FRAGMENTED_TESTS_PATH)
        result = await runner.run(
            Scenario.from_file("fragmented", FRAGMENTED_SCENARIO_PATH), self.client
        )
        self.assertEqual(result, None)

    @unittest_run_loop
    async def test_interaction_templates(self):
        runner = _scenario_runner(INTERACTION_TEMPLATES_TESTS_PATH)
        result = await runner.run(
            Scenario.from_file(
                "interaction_templates", INTERACTION_TEMPLATES_SCENARIO_PATH
            ),
            self.client,
        )
        self.assertEqual(result, None)

    @unittest_run_loop
    async def test_not_identical(self):
        runner = _scenario_runner(FAILURE_TESTS_PATH)

        result: Optional[FailedInteraction] = await runner.run(
            Scenario.from_file("failure", FAILURE_SCENARIO_PATH), self.client
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


class TestRunnerProtocolException(AioHTTPTestCase):
    async def get_application(self):
        async def return_user_input(request: Request):
            return web.Response(content_type="text/plain")

        app = web.Application()
        app.router.add_post("/", return_user_input)
        return app

    def setUp(self):
        super().setUp()
        self.maxDiff = None

    @unittest_run_loop
    async def test_protocol_exception(self):
        with self.assertRaises(ProtocolException):
            runner = _scenario_runner(SUCCESS_TESTS_PATH)
            await runner.run(
                Scenario.from_file("success", SUCCESS_SCENARIO_PATH), self.client
            )


def _scenario_runner(tests_path: Path) -> ScenarioRunner:
    return DependencyInjector(
        Configuration(tests_path / "config.ini"), {"tests_path": tests_path}
    ).autowire(ScenarioRunner)
