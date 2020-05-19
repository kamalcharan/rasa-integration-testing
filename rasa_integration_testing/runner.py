import os
import time
from typing import Any, List, Optional

from aiohttp import ClientSession

from .comparator import JsonDataComparator, JsonDiff
from .helper import generate_tracker_id_from_scenario_name
from .interaction import Interaction, InteractionLoader
from .logging_provider import get_logger
from .protocol import Protocol, ProtocolException
from .scenario import Scenario, ScenarioFragmentLoader, ScenarioFragmentReference

logger = get_logger(__name__)

SENDER_ID_KEY = "sender"

SENDER_ID_ENV_VARIABLE = "SENDER_ID"
STEP_ID_ENV_VARIABLE = "STEP_ID"

IGNORED_KEYS_SEPERATOR = ","

STARTING_STEP_ID = 2


class FailedInteraction:
    def __init__(
        self,
        user_input: Any,
        expected_output: dict,
        actual_output: dict,
        output_diff: JsonDiff,
    ):
        self.user_input = user_input
        self.expected_output = expected_output
        self.actual_output = actual_output
        self.output_diff = output_diff

    def __repr__(self) -> str:
        return (
            f"<FailedInteraction, 'User Input: {self.user_input}, "
            f"Expected output: {self.expected_output}, "
            f"Actual output: {self.actual_output}, "
            f"Output diff: {self.output_diff}'>"
        )


class ScenarioRunner:
    def __init__(
        self,
        protocol: Protocol,
        interaction_loader: InteractionLoader,
        scenario_fragment_loader: ScenarioFragmentLoader,
        comparator: JsonDataComparator,
    ):
        self._protocol = protocol
        self._interaction_loader = interaction_loader
        self._scenario_fragment_loader = scenario_fragment_loader
        self._comparator = comparator

    async def run(
        self, scenario: Scenario, session: ClientSession
    ) -> Optional[FailedInteraction]:
        sender_id = generate_tracker_id_from_scenario_name(time.time(), scenario.name)

        interactions: List[Interaction] = self._resolve_interactions(scenario)

        for step_id, interaction in enumerate(interactions, STARTING_STEP_ID):
            substitutes = {
                SENDER_ID_ENV_VARIABLE: sender_id,
                STEP_ID_ENV_VARIABLE: step_id,
            }
            substitutes.update(os.environ)

            user_input = {SENDER_ID_KEY: sender_id}
            user_input.update(
                self._interaction_loader.render_user_turn(interaction.user, substitutes)
            )

            try:
                actual_output: dict = await self._protocol.send_input(
                    user_input, session
                )
            except ProtocolException as error:
                raise ProtocolException(
                    f'"{scenario}": failed sending user input "{user_input}", '
                    f'protocol error: "{error}"'
                )

            expected_output = self._interaction_loader.render_bot_turn(
                interaction.bot, substitutes
            )
            json_diff: JsonDiff = self._comparator.compare(
                expected_output, actual_output
            )

            if not json_diff.identical:
                failed_interaction = FailedInteraction(
                    user_input, expected_output, actual_output, json_diff
                )
                return failed_interaction

        return None

    def _resolve_interactions(self, scenario: Scenario) -> List[Interaction]:
        interactions: List[Interaction] = []
        for step in scenario.steps:
            if isinstance(step, Interaction):
                interaction: Interaction = step
                interactions.append(interaction)
            elif isinstance(step, ScenarioFragmentReference):
                scenario_fragment_reference: ScenarioFragmentReference = step
                interactions.extend(
                    self._scenario_fragment_loader.scenario_fragment(
                        scenario_fragment_reference.name
                    )
                )
            else:
                raise Exception("Unsupported step type: '{step}'")

        return interactions
