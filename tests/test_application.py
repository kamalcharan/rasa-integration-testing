import sys
from io import StringIO
from unittest import TestCase

from click.testing import CliRunner
from httmock import HTTMock, all_requests, response

from rasa_integration_testing.application import EXIT_FAILURE, EXIT_SUCCESS, cli

CONFIGS_PATH = "tests/main_scenarios"
SUCCESS_CONFIGURATION_PATH = f"{CONFIGS_PATH}/success"
FAILURE_CONFIGURATION_PATH = f"{CONFIGS_PATH}/fail"
MIXED_DIFF_CONFIGURATION_PATH = f"{CONFIGS_PATH}/mixed_diff"


class TestRunner(TestCase):
    def setUp(self):
        self.runner = CliRunner()
        output = StringIO()
        sys.stdout = output
        self.output = output

    def test_successful_scenario(self):
        with HTTMock(request_response):
            execution = self.runner.invoke(cli, [SUCCESS_CONFIGURATION_PATH])
            self.assertEqual(EXIT_SUCCESS, execution.exit_code)

    def test_unsuccessful_scenario(self):
        with HTTMock(request_response):
            execution = self.runner.invoke(cli, [FAILURE_CONFIGURATION_PATH])
            self.assertIsInstance(execution.exception, SystemExit)
            self.assertEqual(EXIT_FAILURE, execution.exit_code)

    def test_mixed_diff_scenario(self):
        with HTTMock(request_response):
            execution = self.runner.invoke(cli, [MIXED_DIFF_CONFIGURATION_PATH])
            self.assertIsInstance(execution.exception, SystemExit)
            self.assertEqual(EXIT_FAILURE, execution.exit_code)


@all_requests
def request_response(url, request):
    headers = {"content-type": "application/json"}
    return response(200, request.body, headers, None, 5, request)
