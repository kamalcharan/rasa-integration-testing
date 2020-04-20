from os import getpid
from socket import gethostname

FILE_EXTENSION_JSON = ".json"
TRACKER_ID_SIGNATURE = "ITEST"


def generate_presentation_label_from_scenario_path(
    scenarios_root_path: str, scenario_path: str
) -> str:
    slicer = slice(len(scenarios_root_path) + 1, len(scenario_path))
    presentation_label = scenario_path[slicer]
    presentation_label = presentation_label.replace("\\", "/")
    presentation_label = presentation_label.replace("/", " / ")
    presentation_label = presentation_label[
        : len(presentation_label) - len(FILE_EXTENSION_JSON)
    ]
    return presentation_label


def generate_scenario_name_from_scenario_path(
    scenarios_root_path: str, scenario_path: str
) -> str:
    # Weird way of doing a substring but this is to overcome a fight
    # beteen our linter and our code formatter ;-)
    slicer = slice(len(scenarios_root_path) + 1, len(scenario_path))
    scenario_name = scenario_path.replace("\\", "_")[slicer]
    scenario_name = scenario_name.replace("/", "_")
    scenario_name = scenario_name[: len(scenario_name) - len(FILE_EXTENSION_JSON)]
    return scenario_name


def generate_tracker_id_from_scenario_name(
    run_timestamp: float, scenario_name: str
) -> str:
    # Build a unique identifier following a format similar to this:
    #
    #     "UTEST_woo20124_1569249227.5879638_ask_installation_basic_flows_success"
    #      --+-- ---+---- ---------+-------- -------+----------------------------
    #        |      |              |                +---- name of the script
    #        |      |              +--------------------- epoch of the test run
    #        |      |                                     execution time
    #        |      +------------------------------------ host of client + process id
    #        +------------------------------------------- unique signature
    unique_identifier = f"{gethostname()}{str(getpid())}_{run_timestamp}"
    return f"{TRACKER_ID_SIGNATURE}_{unique_identifier}_{scenario_name}"
