import json
import os
from json import JSONDecodeError
from time import time
from typing import List, Optional

from requests import Response, post

from .common.configuration import configure
from .common.utils import generate_tracker_id_from_scenario_name
from .comparator import JsonDataComparator, JsonDiff
from .interaction import Interaction, InteractionLoader
from .runner import FailedInteraction, ScenarioRunner
from .scenario import Scenario, ScenarioFragmentLoader

SENDER_ID_KEY = "sender"
SENDER_ID_ENV_VARIABLE = "SENDER_ID"


class RestProtocolException(Exception):
    pass


@configure(
    "protocol.url", InteractionLoader, ScenarioFragmentLoader, JsonDataComparator
)
class RestRunner(ScenarioRunner):
    def run(self, scenario: Scenario) -> Optional[FailedInteraction]:
        sender_id = generate_tracker_id_from_scenario_name(time(), scenario.name)
        interactions: List[Interaction] = self.resolve_interactions(scenario)

        for interaction in interactions:
            substitutes = {
                SENDER_ID_ENV_VARIABLE: sender_id,
            }
            substitutes.update(os.environ)
            user_input = {SENDER_ID_KEY: sender_id}
            user_input.update(
                self.interaction_loader.render_user_turn(interaction.user, substitutes)
            )

            try:
                actual_output: dict = self._send_input(user_input)
            except RestProtocolException as error:
                raise RestProtocolException(
                    f'"{scenario}": failed sending user input "{user_input}", '
                    f'protocol error: "{error}"'
                )

            expected_output = self.interaction_loader.render_bot_turn(
                interaction.bot, substitutes
            )
            json_diff: JsonDiff = self.comparator.compare(
                expected_output, actual_output
            )

            if not json_diff.identical:
                failed_interaction = FailedInteraction(
                    user_input, expected_output, actual_output, json_diff
                )
                return failed_interaction

        return None

    def _send_input(self, json_input: dict) -> dict:
        data = json.dumps(json_input)
        response: Response = post(self.url, data=data)
        try:
            return response.json()
        except JSONDecodeError as error:
            raise RestProtocolException(
                f"{error}, server response received: {response.text}"
            )
