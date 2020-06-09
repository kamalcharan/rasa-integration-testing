import json
import os
from time import time
from typing import List, Optional

from aiohttp import ClientResponse, ClientSession, ContentTypeError

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
class RestScenarioRunner(ScenarioRunner):
    async def run(self, scenario: Scenario) -> Optional[FailedInteraction]:
        async with ClientSession() as session:
            sender_id = generate_tracker_id_from_scenario_name(time(), scenario.name)
            interactions: List[Interaction] = self.resolve_interactions(scenario)

            for interaction in interactions:
                substitutes = {
                    SENDER_ID_ENV_VARIABLE: sender_id,
                }
                substitutes.update(os.environ)
                user_input = {SENDER_ID_KEY: sender_id}
                user_input.update(
                    self.interaction_loader.render_user_turn(
                        interaction.user, substitutes
                    )
                )

                try:
                    actual_output: dict = await self._send_input(user_input, session)
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

    async def _send_input(self, json_input: dict, session: ClientSession) -> dict:
        data = json.dumps(json_input)
        response: ClientResponse = await session.post(self.url, data=data)
        try:
            return await response.json()
        except ContentTypeError as error:
            message = await response.text()
            raise RestProtocolException(f"{error}, server response received: {message}")
