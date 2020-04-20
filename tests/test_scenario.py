from pathlib import Path
from unittest import TestCase

from rasa_integration_testing.interaction import Interaction, InteractionTurn
from rasa_integration_testing.scenario import (
    Scenario,
    ScenarioFragmentReference,
    ScenarioParsingError,
)

SCENARIO_ROOT = "tests/test_scenarios"

SIMPLE_SCENARIO = Path(f"{SCENARIO_ROOT}/simple.yml")
FRAGMENTED_SCENARIO = Path(f"{SCENARIO_ROOT}/fragmented.yml")
INTERACTION_TEMPLATES_SCENARIO = Path(f"{SCENARIO_ROOT}/interaction_templates.yml")
INVALID_PROPERTIES_SCENARIO = Path(f"{SCENARIO_ROOT}/invalid_properties.yml")
INVALID_NOT_A_LIST_SCENARIO = Path(f"{SCENARIO_ROOT}/invalid_not_a_list.yml")


class TestScenario(TestCase):
    def test_simple_scenario(self):
        scenario_name = "simple"
        scenario: Scenario = Scenario.from_file(scenario_name, SIMPLE_SCENARIO)

        self.assertEqual(scenario.name, scenario_name)
        self.assertListEqual(
            scenario.steps,
            [
                Interaction(
                    InteractionTurn("initial_parameters"), InteractionTurn("welcome")
                ),
                Interaction(InteractionTurn("goodbye"), InteractionTurn("thank_you")),
            ],
        )

    def test_fragmented_scenario(self):
        scenario_name = "fragmented"
        scenario: Scenario = Scenario.from_file(scenario_name, FRAGMENTED_SCENARIO)

        self.assertEqual(scenario.name, scenario_name)
        self.assertListEqual(
            scenario.steps,
            [
                ScenarioFragmentReference("introduction"),
                Interaction(InteractionTurn("user1"), InteractionTurn("bot1")),
                ScenarioFragmentReference("another/fragment"),
                Interaction(InteractionTurn("user2"), InteractionTurn("bot2")),
                ScenarioFragmentReference("conclusion"),
            ],
        )

    def test_interaction_templates_scenario(self):
        scenario_name = "interaction_templates"
        scenario: Scenario = Scenario.from_file(
            scenario_name, INTERACTION_TEMPLATES_SCENARIO
        )

        self.assertEqual(scenario.name, scenario_name)

        variables = {"title": "Mister", "name": "John"}

        self.assertListEqual(
            scenario.steps,
            [
                Interaction(
                    InteractionTurn("welcome_template", variables),
                    InteractionTurn("welcome"),
                ),
                Interaction(
                    InteractionTurn("goodbye"),
                    InteractionTurn("goodbye_template", variables),
                ),
            ],
        )

    def test_invalid_properties_scenario(self):
        with self.assertRaisesRegex(
            ScenarioParsingError,
            f"Invalid scenario step definition: .*{INVALID_PROPERTIES_SCENARIO}",
        ):
            Scenario.from_file("invalid_properties", INVALID_PROPERTIES_SCENARIO)

    def test_invalid_not_a_list_scenario(self):
        with self.assertRaisesRegex(
            ScenarioParsingError,
            f"Invalid scenario format: {INVALID_NOT_A_LIST_SCENARIO}",
        ):
            Scenario.from_file("invalid_not_a_list", INVALID_NOT_A_LIST_SCENARIO)
