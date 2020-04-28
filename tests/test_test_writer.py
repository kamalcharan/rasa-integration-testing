import json
import os
import tempfile
from pathlib import Path
from unittest import TestCase

from rasa_integration_testing.scenario import Interaction, InteractionTurn, Scenario
from rasa_integration_testing.test_writer import (
    BOT,
    INTERACTION_EXTENSION,
    SCENARIO_FILENAME,
    USER,
    write_bot_output,
    write_user_input,
)

SENDER_ID = "abcdef123456"

USER_INPUT_1 = {USER: "first"}
USER_INPUT_2 = {USER: "last"}

BOT_OUTPUT_1 = {BOT: "first"}
BOT_OUTPUT_2 = {BOT: "last"}


class TestTestWriter(TestCase):
    def test_write_scenario(self):
        with tempfile.TemporaryDirectory() as test_output_directory:
            write_user_input(test_output_directory, SENDER_ID, USER_INPUT_1)
            write_bot_output(test_output_directory, SENDER_ID, BOT_OUTPUT_1)

            write_user_input(test_output_directory, SENDER_ID, USER_INPUT_2)
            write_bot_output(test_output_directory, SENDER_ID, BOT_OUTPUT_2)

            scenario = Scenario.from_file(
                "test_writer",
                Path(f"{test_output_directory}/{SENDER_ID}/{SCENARIO_FILENAME}"),
            )

            self.assertEqual(
                [
                    Interaction(InteractionTurn("user1"), InteractionTurn("bot1")),
                    Interaction(InteractionTurn("user2"), InteractionTurn("bot2")),
                ],
                scenario.steps,
            )

            self.assertEqual(
                2, len(os.listdir(f"{test_output_directory}/{SENDER_ID}/{USER}"))
            )

            self.assertEqual(
                2, len(os.listdir(f"{test_output_directory}/{SENDER_ID}/{BOT}"))
            )

            with open(
                f"{test_output_directory}/{SENDER_ID}/{USER}/"
                f"{USER}1.{INTERACTION_EXTENSION}"
            ) as interaction_file:
                self.assertEqual(USER_INPUT_1, json.load(interaction_file))
