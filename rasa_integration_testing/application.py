import asyncio
import sys
from enum import Enum
from itertools import chain
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, TextIO, Tuple

import click
import socketio
from aiohttp import ClientSession

from .common.cli import (
    COLOR_ERROR,
    COLOR_SUCCESS,
    COLOR_WARNING,
    EXIT_FAILURE,
    EXIT_SUCCESS,
    echo,
)
from .common.configuration import Configuration, DependencyInjector, configure
from .common.utils import quick_chunk
from .rest_runner import RestScenarioRunner
from .runner import FailedInteraction, ScenarioRunner
from .scenario import Scenario, load_scenarios
from .socketio_runner import SocketIORunner

SCENARIOS_FOLDER = "scenarios"
SCENARIOS_GLOB = "*.yml"
DEFAULT_ASYNC_CHUNK_SIZE = 8

RUNNER_CONFIG_SECTION = "runner"
TEST_CONFIG_FILE = "config.ini"
TESTS_PATH_ARGUMENT = "tests_path"


@click.command()
@click.argument(TESTS_PATH_ARGUMENT, type=click.Path(exists=True))
@click.option(
    "-k",
    "--chunk-size",
    type=click.INT,
    default=DEFAULT_ASYNC_CHUNK_SIZE,
    help="Size of asynchronous test chunks.",
)
@click.option("-o", "--output", type=click.File("w"), default=sys.stdout)
@click.argument("scenarios_glob", required=False, default=SCENARIOS_GLOB)
def cli(tests_path: str, chunk_size: int, output: TextIO, scenarios_glob: str) -> None:
    folder_path = Path(tests_path)
    configuration = Configuration(folder_path / TEST_CONFIG_FILE)
    injector = DependencyInjector(configuration, {TESTS_PATH_ARGUMENT: folder_path})
    scenarios_path = folder_path / SCENARIOS_FOLDER
    scenarios: List[Scenario] = load_scenarios(scenarios_path, scenarios_glob)

    runner_type: Callable[..., ScenarioRunner] = injector.autowire(runner_selector)
    runner: ScenarioRunner = injector.autowire(runner_type)

    loop = asyncio.get_event_loop()
    failed_interactions: List[FailedInteraction] = loop.run_until_complete(
        _run_scenarios(runner, scenarios, chunk_size, output)
    )
    sys.exit(EXIT_FAILURE if failed_interactions else EXIT_SUCCESS)


@configure("protocol.type")
def _get_session_type(protocol_type: str) -> Any:
    return socketio.AsyncClient if protocol_type == "socketio" else ClientSession


async def _run_scenarios(
    runner: ScenarioRunner, scenarios: List[Scenario], chunk_size: int, output: TextIO,
) -> List[FailedInteraction]:
    chunk_scenarios: Iterable[Tuple[Scenario, ...]] = quick_chunk(
        tuple(scenarios), chunk_size
    )
    async_results: List[List[FailedInteraction]] = [
        await _run_scenario_chunk(chunk, runner, output) for chunk in chunk_scenarios
    ]

    return list(chain.from_iterable(async_results))


async def _run_scenario_chunk(
    chunked_scenarios: Tuple[Scenario, ...], runner: ScenarioRunner, output: TextIO,
) -> List[FailedInteraction]:
    async_results = await asyncio.gather(
        *[
            _run_scenario(runner, scenario, output)
            for scenario in chunked_scenarios
            if scenario is not None
        ]
    )
    return [result for result in async_results if result is not None]


async def _run_scenario(
    runner: ScenarioRunner, scenario: Scenario, output: TextIO,
) -> Optional[FailedInteraction]:
    echo(f"Running scenario '{scenario.name}'...", COLOR_WARNING, output)
    result: Optional[FailedInteraction] = await runner.run(scenario)

    if result is None:
        echo(f"+++ Successfully ran scenario '{scenario.name}'!", COLOR_SUCCESS, output)
    else:
        echo(
            f"--- Scenario '{scenario.name}' failed the following interaction.",
            COLOR_ERROR,
            output,
        )
        _print_failed_interaction(result, output)

    return result


def _print_failed_interaction(
    failed_interaction: FailedInteraction, output: TextIO
) -> None:
    echo("User sent:", COLOR_WARNING, output=output)
    echo(f"{failed_interaction.user_input}", output=output)
    echo("Expected output:", COLOR_WARNING, output)
    echo(f"{failed_interaction.expected_output}", output=output)
    echo("Actual output:", COLOR_WARNING, output)
    echo(f"{failed_interaction.actual_output}", output=output)
    echo("Bot output was different than expected:", COLOR_WARNING, output)

    if failed_interaction.output_diff.missing_entries:
        for key, value in failed_interaction.output_diff.missing_entries.items():
            echo(f" - {key}: {value}", COLOR_ERROR, output)
            if key in failed_interaction.output_diff.extra_entries:
                extra_value = failed_interaction.output_diff.extra_entries.pop(key)
                _output_extra_value(key, extra_value, output)

    if failed_interaction.output_diff.extra_entries:
        for key, value in failed_interaction.output_diff.extra_entries.items():
            _output_extra_value(key, value, output)

    echo("---", COLOR_ERROR, output)


def _output_extra_value(key: Any, value: Any, output: TextIO) -> None:
    echo(f" + {key}: {value}", COLOR_SUCCESS, output)


class RunnerType(Enum):
    REST = ("rest", RestScenarioRunner)
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
