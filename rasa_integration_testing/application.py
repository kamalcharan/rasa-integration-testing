import asyncio
import sys
from itertools import chain
from pathlib import Path
from typing import Any, Iterable, List, Optional, TextIO, Tuple

import click
from aiohttp import ClientSession

from .cli import (
    COLOR_ERROR,
    COLOR_SUCCESS,
    COLOR_WARNING,
    EXIT_FAILURE,
    EXIT_SUCCESS,
    echo,
)
from .common import quick_chunk
from .comparator import JsonDataComparator
from .configuration import Configuration, DependencyInjector
from .interaction import InteractionLoader
from .logging_provider import get_logger
from .protocol import protocol_selector
from .runner import FailedInteraction, ScenarioRunner
from .scenario import Scenario, ScenarioFragmentLoader, load_scenarios

logger = get_logger(__name__)

SCENARIOS_FOLDER = "scenarios"
SCENARIOS_GLOB = "*.yml"
DEFAULT_ASYNC_CHUNK_SIZE = 16

RUNNER_CONFIG_SECTION = "runner"
TEST_CONFIG_FILE = "config.ini"


@click.command()
@click.argument("tests_path", type=click.Path(exists=True))
@click.option(
    "-k",
    "--chunk-size",
    type=click.INT,
    default=DEFAULT_ASYNC_CHUNK_SIZE,
    help="Size of asynchronous test chunks.",
)
@click.option("-o", "--output", type=click.File("w"), default=sys.stdout)
@click.argument("scenarios_glob", required=False, default=SCENARIOS_GLOB)
def cli(tests_path: str, chunk_size: int, output: TextIO, scenarios_glob: str):
    folder_path = Path(tests_path)
    configuration = Configuration(folder_path.joinpath(TEST_CONFIG_FILE))
    injector = DependencyInjector(configuration)
    scenarios_path = folder_path.joinpath(SCENARIOS_FOLDER)
    scenarios: List[Scenario] = load_scenarios(scenarios_path, scenarios_glob)

    runner: ScenarioRunner = ScenarioRunner(
        injector.autowire(protocol_selector),
        InteractionLoader(folder_path),
        ScenarioFragmentLoader(folder_path),
        injector.autowire(JsonDataComparator),
    )

    loop = asyncio.get_event_loop()
    failed_interactions: List[FailedInteraction] = loop.run_until_complete(
        _run_scenarios(runner, scenarios, chunk_size, output)
    )

    if failed_interactions:
        sys.exit(EXIT_FAILURE)
    else:
        sys.exit(EXIT_SUCCESS)


async def _run_scenarios(
    runner: ScenarioRunner, scenarios: List[Scenario], chunk_size: int, output: TextIO
) -> List[FailedInteraction]:
    async with ClientSession() as session:
        chunk_scenarios: Iterable[Tuple[Scenario, ...]] = quick_chunk(
            tuple(scenarios), chunk_size
        )
        async_results: List[List[FailedInteraction]] = [
            await _run_scenario_chunk(chunk, runner, session, output)
            for chunk in chunk_scenarios
        ]

        return list(chain.from_iterable(async_results))


async def _run_scenario_chunk(
    chunked_scenarios: Tuple[Scenario, ...],
    runner: ScenarioRunner,
    session: ClientSession,
    output: TextIO,
) -> List[FailedInteraction]:
    async_results = await asyncio.gather(
        *[
            _run_scenario(runner, scenario, session, output)
            for scenario in chunked_scenarios
            if scenario is not None
        ]
    )
    return [result for result in async_results if result is not None]


async def _run_scenario(
    runner: ScenarioRunner, scenario: Scenario, session: ClientSession, output: TextIO
) -> Optional[FailedInteraction]:
    echo(f"Running scenario '{scenario.name}'...", COLOR_WARNING, output)
    result: Optional[FailedInteraction] = await runner.run(scenario, session)

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
