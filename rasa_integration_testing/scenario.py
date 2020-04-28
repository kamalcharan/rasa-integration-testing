import os
from pathlib import Path
from typing import Dict, List, Union

from ruamel.yaml import YAML

from .interaction import Interaction, InteractionTurn
from .logging_provider import get_logger

logger = get_logger(__name__)

SCENARIO_FRAGMENTS_FOLDER = "scenario_fragments"
SCENARIO_FRAGMENTS_GLOB = "*.yml"

EXTENSION_SEPARATOR = "."

USER_KEY = "user"
BOT_KEY = "bot"
TEMPLATE_KEY = "template"
VARIABLES_KEY = "variables"


class ScenarioParsingError(Exception):
    def __init__(self, message: str, path: Path):
        super().__init__(f"{message}: {path}")


class ScenarioFragmentReference:
    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def __repr__(self):
        return f"ScenarioFragmentReference: name={self.name}"

    def __eq__(self, other) -> bool:
        return self.__class__ == other.__class__ and self.name == other.name

    def __hash__(self):
        return hash((self.name))


class Scenario:
    def __init__(
        self, name: str, steps: List[Union[Interaction, ScenarioFragmentReference]]
    ):
        self.name = name
        self.steps = steps

    @classmethod
    def from_file(cls, name: str, path: Path) -> "Scenario":
        logger.info("Loading scenario from: {path}", path=path)

        with open(path) as scenario_file:
            yaml = YAML()
            steps = yaml.load(scenario_file)

            if not isinstance(steps, list):
                raise ScenarioParsingError("Invalid scenario format", path)

            try:
                return cls(name, [_create_scenario_step(step, path) for step in steps])
            except TypeError as type_error:
                raise ScenarioParsingError(str(type_error), path)

    def __repr__(self):
        return f"Scenario '{self.name}': steps={self.steps}"


class ScenarioFragmentLoader:
    def __init__(self, test_definitions_path: Path):
        self._scenario_fragments_path = test_definitions_path.joinpath(
            SCENARIO_FRAGMENTS_FOLDER
        )
        self._scenario_fragments = self._load_scenario_fragments()

    def scenario_fragment(self, scenario_fragment_name: str) -> List[Interaction]:
        return self._scenario_fragments[scenario_fragment_name]

    def _load_scenario_fragments(self) -> Dict[str, List[Interaction]]:
        def get_interactions(scenario: Scenario) -> List[Interaction]:
            steps = scenario.steps
            interactions: List[Interaction] = [
                step for step in steps if isinstance(step, Interaction)
            ]

            if len(interactions) != len(steps):
                raise Exception(
                    f"Scenario fragment '{scenario.name}'"
                    "cannot refer to other fragments (for now)"
                )

            return interactions

        return {
            scenario.name: get_interactions(scenario)
            for scenario in load_scenarios(
                self._scenario_fragments_path, SCENARIO_FRAGMENTS_GLOB
            )
        }


def load_scenarios(scenarios_path: Path, scenarios_glob: str) -> List[Scenario]:
    return [
        Scenario.from_file(_scenario_name(scenario_file, scenarios_path), scenario_file)
        for scenario_file in list(scenarios_path.rglob(scenarios_glob))
    ]


def _scenario_name(scenario_file: Path, scenarios_path: Path) -> str:
    scenario_name = os.path.relpath(scenario_file, str(scenarios_path))
    return scenario_name[: scenario_name.rfind(EXTENSION_SEPARATOR)]


def _create_scenario_step(
    step: Union[dict, str], scenario_path: Path
) -> Union[Interaction, ScenarioFragmentReference]:
    if isinstance(step, str):
        return ScenarioFragmentReference(step)

    if isinstance(step, dict) and step.keys() == {USER_KEY, BOT_KEY}:
        user_turn = _create_interaction_turn(step[USER_KEY], scenario_path)
        bot_turn = _create_interaction_turn(step[BOT_KEY], scenario_path)
        return Interaction(user_turn, bot_turn)

    raise ScenarioParsingError(
        f"Invalid scenario step definition: {step}", scenario_path
    )


def _create_interaction_turn(
    definition: Union[dict, str], scenario_path: Path
) -> InteractionTurn:
    if isinstance(definition, str):
        template: str = definition
        return InteractionTurn(template)

    if isinstance(definition, dict) and definition.keys() == {
        TEMPLATE_KEY,
        VARIABLES_KEY,
    }:
        return InteractionTurn(**definition)

    raise ScenarioParsingError(
        f"Invalid interaction turn definition: {definition}", scenario_path
    )
