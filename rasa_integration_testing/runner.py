from typing import Any, List, Optional, Union

from .comparator import JsonDataComparator, JsonDiff
from .interaction import Interaction, InteractionLoader
from .scenario import Scenario, ScenarioFragmentLoader, ScenarioFragmentReference


class FailedInteraction:
    def __init__(
        self,
        user_input: Any,
        expected_output: Union[dict, list],
        actual_output: Union[dict, list],
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
        url: str,
        interaction_loader: InteractionLoader,
        scenario_fragment_loader: ScenarioFragmentLoader,
        comparator: JsonDataComparator,
    ):
        self.url = url
        self.interaction_loader = interaction_loader
        self.scenario_fragment_loader = scenario_fragment_loader
        self.comparator = comparator

    def run(self, scenario: Scenario) -> Optional[FailedInteraction]:
        raise NotImplementedError

    def resolve_interactions(self, scenario: Scenario) -> List[Interaction]:
        interactions: List[Interaction] = []
        for step in scenario.steps:
            if isinstance(step, Interaction):
                interaction: Interaction = step
                interactions.append(interaction)
            elif isinstance(step, ScenarioFragmentReference):
                scenario_fragment_reference: ScenarioFragmentReference = step
                interactions.extend(
                    self.scenario_fragment_loader.scenario_fragment(
                        scenario_fragment_reference.name
                    )
                )
            else:
                raise Exception("Unsupported step type: '{step}'")

        return interactions
