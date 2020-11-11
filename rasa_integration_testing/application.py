import logging
import sys
from concurrent.futures.thread import ThreadPoolExecutor
from enum import Enum
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import Callable, Dict, List, Optional

import click
import coloredlogs

from .common.configuration import Configuration, DependencyInjector, configure
from .rest_runner import IvrRunner, RestRunner
from .runner import FailedInteraction, ScenarioRunner
from .scenario import Scenario, load_scenarios
from .socketio_runner import SocketIORunner

SCENARIOS_FOLDER = "scenarios"
SCENARIOS_GLOB = "*.yml"
DEFAULT_MAX_WORKERS = 8

RUNNER_CONFIG_SECTION = "runner"
TEST_CONFIG_FILE = "config.ini"
TESTS_PATH_ARGUMENT = "tests_path"

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
COLOR_SUCCESS = "green"
COLOR_FAILURE = "red"
COLOR_EXTRA = "cyan"
COLOR_WARNING = "yellow"

MESSAGE_KEY = "message"
FOREGROUND_COLOR_KEY = "fg"

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)
coloredlogs.install(level="INFO", logger=logger)

output_queue: Queue = Queue()


@click.command()
@click.argument(TESTS_PATH_ARGUMENT, type=click.Path(exists=True))
@click.option(
    "-k",
    "--max-workers",
    type=click.INT,
    default=DEFAULT_MAX_WORKERS,
    help="Amount of simultaenous workers.",
)
@click.argument("scenarios_glob", required=False, default=SCENARIOS_GLOB)
def cli(tests_path: str, max_workers: int, scenarios_glob: str) -> None:
    folder_path = Path(tests_path)
    configuration = Configuration(folder_path / TEST_CONFIG_FILE)
    injector = DependencyInjector(configuration, {TESTS_PATH_ARGUMENT: folder_path})
    scenarios_path = folder_path / SCENARIOS_FOLDER
    scenarios: List[Scenario] = load_scenarios(scenarios_path, scenarios_glob)

    runner_type: Callable[..., ScenarioRunner] = injector.autowire(runner_selector)
    runner: ScenarioRunner = injector.autowire(runner_type)

    output_thread = Thread(target=write_queue_output, daemon=True)
    output_thread.start()

    failed_interactions: List[FailedInteraction] = _run_scenarios(
        runner, scenarios, max_workers
    )

    output_queue.join()
    if failed_interactions:
        click.secho(f"{len(failed_interactions)} tests failed!", fg=COLOR_FAILURE)
    else:
        click.secho(f"{len(scenarios)} tests ran successfully.", fg=COLOR_SUCCESS)

    sys.exit(EXIT_FAILURE if failed_interactions or not scenarios else EXIT_SUCCESS)


def write_queue_output():
    while True:
        click.secho(**output_queue.get())
        output_queue.task_done()


def _run_scenarios(
    runner: ScenarioRunner, scenarios: List[Scenario], max_workers: int
) -> List[FailedInteraction]:
    with ThreadPoolExecutor(max_workers) as executor:
        return [
            result
            for result in executor.map(
                _run_interaction, [runner] * len(scenarios), scenarios
            )
            if result is not None
        ]


def _run_interaction(
    runner: ScenarioRunner, scenario: Scenario
) -> Optional[FailedInteraction]:
    output_queue.put(
        {
            MESSAGE_KEY: f"Running scenario '{scenario.name}'...",
            FOREGROUND_COLOR_KEY: COLOR_WARNING,
        }
    )
    result: Optional[FailedInteraction] = runner.run(scenario)

    if result is None:
        output_queue.put(
            {
                MESSAGE_KEY: f"+++ Successfully ran scenario '{scenario.name}'!",
                FOREGROUND_COLOR_KEY: COLOR_SUCCESS,
            }
        )
    else:
        output_queue.put(
            {
                MESSAGE_KEY: f"--- Scenario '{scenario.name}' failed the following interaction.",
                FOREGROUND_COLOR_KEY: COLOR_FAILURE,
            }
        )
        _print_failed_interaction(result)

    return result


def _print_failed_interaction(failed_interaction: FailedInteraction) -> None:
    output_queue.put({MESSAGE_KEY: "User sent:"})
    output_queue.put({MESSAGE_KEY: f"{failed_interaction.user_input}"})
    output_queue.put(
        {MESSAGE_KEY: "Expected output:", FOREGROUND_COLOR_KEY: COLOR_WARNING}
    )
    output_queue.put({MESSAGE_KEY: f"{failed_interaction.expected_output}"})
    output_queue.put(
        {MESSAGE_KEY: "Actual output:", FOREGROUND_COLOR_KEY: COLOR_WARNING}
    )
    output_queue.put({MESSAGE_KEY: f"{failed_interaction.actual_output}"})
    output_queue.put(
        {
            MESSAGE_KEY: "Bot output was different than expected:",
            FOREGROUND_COLOR_KEY: COLOR_WARNING,
        }
    )

    if failed_interaction.output_diff.missing_entries:
        for key, value in failed_interaction.output_diff.missing_entries.items():
            output_queue.put(_format_message(f" - {key}: {value}"))
            if key in failed_interaction.output_diff.extra_entries:
                extra_value = failed_interaction.output_diff.extra_entries.pop(key)
                output_queue.put(
                    _format_message(f" + {key}: {extra_value}", COLOR_EXTRA)
                )

    if failed_interaction.output_diff.extra_entries:
        for key, value in failed_interaction.output_diff.extra_entries.items():
            output_queue.put(_format_message(f" + {key}: {value}", COLOR_EXTRA))

    output_queue.put(_format_message("---"))


def _format_message(message: str, color: str = None) -> Dict:
    return {MESSAGE_KEY: message, FOREGROUND_COLOR_KEY: color or COLOR_FAILURE}


class RunnerType(Enum):
    REST = ("rest", RestRunner)
    IVR = ("ivr", IvrRunner)
    SOCKETIO = ("socketio", SocketIORunner)

    def __init__(self, key: str, runner_constructor: Callable):
        self.key = key
        self.runner_constructor = runner_constructor

    @classmethod
    def to_dict(cls) -> Dict[str, Callable]:
        return {entry.key: entry.runner_constructor for entry in cls}

    @classmethod
    def from_string(cls, runner_type: str) -> Callable[..., ScenarioRunner]:
        selector_callables: Dict[str, Callable] = cls.to_dict()
        if runner_type in selector_callables:
            return selector_callables[runner_type]

        raise Exception(f"'{runner_type}' isn't a valid runner type.")


@configure("protocol.type")
def runner_selector(protocol_type: str) -> Callable[..., ScenarioRunner]:
    return RunnerType.from_string(protocol_type)
