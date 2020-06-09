import asyncio
import json
import os
import re
from unittest import TestCase

from aiohttp import web
from aiohttp.test_utils import Request, TestServer
from click.testing import CliRunner

from rasa_integration_testing.application import cli
from rasa_integration_testing.common.cli import EXIT_FAILURE, EXIT_SUCCESS

SENDER_ID_PATTERN = r"\{<Key.SENDER: 'sender'>: '.*'\}"

CONFIGS_PATH = "tests/main_scenarios"
SUCCESS_CONFIGURATION_PATH = f"{CONFIGS_PATH}/success"
FAILURE_CONFIGURATION_PATH = f"{CONFIGS_PATH}/fail"
MIXED_DIFF_CONFIGURATION_PATH = f"{CONFIGS_PATH}/mixed_diff"
TEST_DATA_PATH = "tests/test_main_data"
TEST_OUTPUT = f"{TEST_DATA_PATH}/output"


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
        self.runner = CliRunner()

    def tearDown(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.server.close())

        with open(
            f"{TEST_DATA_PATH}/{self._testMethodName}", "r"
        ) as expected_file, open(TEST_OUTPUT, "r") as actual_file:
            actual_file.seek(0)
            for expected_line in expected_file.readlines():
                actual_line = actual_file.readline()
                if not re.match(SENDER_ID_PATTERN, expected_line):
                    self.assertEqual(expected_line.strip(), actual_line.strip())

    def test_successful_scenario(self):
        execution = self.runner.invoke(
            cli, [SUCCESS_CONFIGURATION_PATH, "-o", TEST_OUTPUT]
        )
        self.assertEqual(EXIT_SUCCESS, execution.exit_code)

    def test_unsuccessful_scenario(self):
        execution = self.runner.invoke(
            cli, [FAILURE_CONFIGURATION_PATH, "-o", TEST_OUTPUT]
        )
        self.assertIsInstance(execution.exception, SystemExit)
        self.assertEqual(EXIT_FAILURE, execution.exit_code)

    def test_mixed_diff_scenario(self):
        execution = self.runner.invoke(
            cli, [MIXED_DIFF_CONFIGURATION_PATH, "-o", TEST_OUTPUT]
        )
        self.assertIsInstance(execution.exception, SystemExit)
        self.assertEqual(EXIT_FAILURE, execution.exit_code)

    @classmethod
    def tearDownClass(cls):
        os.remove(TEST_OUTPUT)
