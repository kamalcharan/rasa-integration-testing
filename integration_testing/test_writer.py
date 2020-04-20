import json
import os

from ruamel.yaml import YAML

USER = "user"
BOT = "bot"

INTERACTION_EXTENSION = "json"
SCENARIO_FILENAME = "scenario.yml"


def write_user_input(test_output_directory: str, sender_id: str, user_input: dict):
    _write_interaction(test_output_directory, sender_id, USER, user_input)


def write_bot_output(test_output_directory: str, sender_id: str, bot_output: dict):
    interaction_count = _write_interaction(
        test_output_directory, sender_id, BOT, bot_output
    )

    _write_scenario(test_output_directory, sender_id, interaction_count)


def _write_interaction(
    test_output_directory: str,
    sender_id: str,
    interaction_type: str,
    interaction_content: dict,
) -> int:
    session_directory = f"{test_output_directory}/{sender_id}"
    interaction_type_directory = f"{session_directory}/{interaction_type}"
    os.makedirs(interaction_type_directory, exist_ok=True)

    interaction_count = len(os.listdir(interaction_type_directory)) + 1

    interaction_filename = (
        f"{interaction_type_directory}/"
        f"{interaction_type}{interaction_count}.{INTERACTION_EXTENSION}"
    )

    with open(interaction_filename, "w") as interaction_file:
        interaction_file.write(
            json.dumps(interaction_content, sort_keys=True, indent=2)
        )

    return interaction_count


def _write_scenario(test_output_directory: str, sender_id: str, interaction_count: int):
    interactions = [
        {USER: USER + str(interaction_index), BOT: BOT + str(interaction_index)}
        for interaction_index in range(1, interaction_count + 1)
    ]

    scenario_filename = f"{test_output_directory}/{sender_id}/{SCENARIO_FILENAME}"
    with open(scenario_filename, "w") as scenario_file:
        yaml = YAML()
        yaml.dump(interactions, scenario_file)
