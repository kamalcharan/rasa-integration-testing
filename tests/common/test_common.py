import time
from os import getpid
from socket import gethostname
from unittest import TestCase

from rasa_integration_testing.common.utils import (
    TRACKER_ID_SIGNATURE,
    generate_tracker_id_from_scenario_name,
    quick_chunk,
)

INPUT_SCENARIOS_ROOT_PATH = "scenarios"
INPUT_SCENARIO_PATH = "scenarios/broken_mouse\\wireless/basic_flows/success.json"
INPUT_SCENARIO_NAME = "broken_mouse_wireless_basic_flows_success"

EXPECTED_SCENARIO_NAME = "broken_mouse_wireless_basic_flows_success"
EXPECTED_PRESENTATION_LABEL = "broken_mouse / wireless / basic_flows / success"


class TestCommon(TestCase):
    def test_generate_tracker_id_from_scenario_name(self):
        tracker_id = generate_tracker_id_from_scenario_name(
            time.time(), INPUT_SCENARIO_NAME
        )
        self.assertIsNotNone(tracker_id)

        regex = f"^{TRACKER_ID_SIGNATURE}_{gethostname()}\
{str(getpid())}_\\d*.\\d*_{EXPECTED_SCENARIO_NAME}"
        self.assertRegex(tracker_id, regex)

    def test_quick_chunk(self):
        chunks = quick_chunk(("a", "b", "c"), 2)
        self.assertEqual(tuple(chunks), (("a", "b"), ("c", None)))

    def test_quick_chunk_under_chunk_size(self):
        chunks = quick_chunk(("a"), 3)
        self.assertEqual(tuple(chunks), (("a", None, None),))
