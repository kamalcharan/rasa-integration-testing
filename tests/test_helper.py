import time
from os import getpid
from socket import gethostname
from unittest import TestCase

from integration_testing.helper import (
    TRACKER_ID_SIGNATURE,
    generate_presentation_label_from_scenario_path,
    generate_scenario_name_from_scenario_path,
    generate_tracker_id_from_scenario_name,
)

INPUT_SCENARIOS_ROOT_PATH = "scenarios"
INPUT_SCENARIO_PATH = "scenarios/broken_mouse\\wireless/basic_flows/success.json"
INPUT_SCENARIO_NAME = "broken_mouse_wireless_basic_flows_success"

EXPECTED_SCENARIO_NAME = "broken_mouse_wireless_basic_flows_success"
EXPECTED_PRESENTATION_LABEL = "broken_mouse / wireless / basic_flows / success"


class TestHelper(TestCase):
    def test_generate_presentation_label_from_scenario_path(self):

        label = generate_presentation_label_from_scenario_path(
            INPUT_SCENARIOS_ROOT_PATH, INPUT_SCENARIO_PATH
        )

        self.assertEqual(label, EXPECTED_PRESENTATION_LABEL)

    def test_generate_scenario_name_from_scenario_path(self):
        scenario_name = generate_scenario_name_from_scenario_path(
            INPUT_SCENARIOS_ROOT_PATH, INPUT_SCENARIO_PATH
        )

        self.assertEqual(scenario_name, EXPECTED_SCENARIO_NAME)

    def test_generate_tracker_id_from_scenario_name(self):
        tracker_id = generate_tracker_id_from_scenario_name(
            time.time(), INPUT_SCENARIO_NAME
        )
        self.assertIsNotNone(tracker_id)

        regex = f"^{TRACKER_ID_SIGNATURE}_{gethostname()}\
{str(getpid())}_\\d*.\\d*_{EXPECTED_SCENARIO_NAME}"

        self.assertRegex(tracker_id, regex)
