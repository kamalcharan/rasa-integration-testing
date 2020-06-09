import asyncio
from pathlib import Path
from typing import Any, List
from unittest import TestCase

from socketio import ASGIApp, AsyncServer
from uvicorn import Config, Server

from rasa_integration_testing.common.configuration import (
    Configuration,
    DependencyInjector,
)
from rasa_integration_testing.interaction import INTERACTION_TURN_EXTENSION, Interaction
from rasa_integration_testing.scenario import Scenario
from rasa_integration_testing.socketio_runner import (
    EVENT_BOT_UTTERED,
    EVENT_USER_UTTERED,
    SocketIORunner,
)

YML_EXTENSION = "yml"
INI_EXTENSION = "ini"

TEST_DEFINITIONS_FOLDER = Path("tests/socketio_scenarios/")
SUCCESS_TESTS_PATH = TEST_DEFINITIONS_FOLDER / "success"

SUCCESS_SCENARIO_PATH = SUCCESS_TESTS_PATH / f"scenarios/success.{YML_EXTENSION}"

WELCOME_JSON_DATA = (
    TEST_DEFINITIONS_FOLDER
    / f"fail/interactions/bot/welcome.{INTERACTION_TURN_EXTENSION}"
)
INITIAL_INVALID_DATA = (
    TEST_DEFINITIONS_FOLDER
    / f"fail/interactions/user/initial_invalid.{INTERACTION_TURN_EXTENSION}"
)


class TestRunner(TestCase):
    def setUp(self):
        self.maxDiff = None
        sio = AsyncServer(async_mode="asgi")

        @sio.on(EVENT_USER_UTTERED)
        async def on_user_uttered(session_id: str, request: Any):
            if self.bot_messages_stack:
                messages = self.bot_messages_stack.pop(0)
                for message in messages:
                    await sio.emit(EVENT_BOT_UTTERED, message, room=session_id)

        app = ASGIApp(sio)
        config = Config(app, host="localhost", port=8081)
        server = Server(config=config)
        config.setup_event_loop()
        server_task = server.serve()
        asyncio.ensure_future(server_task)

    def tearDown(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.run())

    def test_identical(self):
        runner = _scenario_runner(SUCCESS_TESTS_PATH)
        scenario = Scenario.from_file("success", SUCCESS_SCENARIO_PATH)
        self.bot_messages_stack = _bot_message_stack(runner, scenario)

        async def run():
            await asyncio.sleep(1)
            result = await runner.run(scenario)
            self.assertEqual(result, None)

        self.run = run


def _scenario_runner(tests_path: Path) -> SocketIORunner:
    return DependencyInjector(
        Configuration(tests_path / f"config.{INI_EXTENSION}"),
        {"tests_path": tests_path},
    ).autowire(SocketIORunner)


def _bot_message_stack(runner: SocketIORunner, scenario: Scenario) -> List[dict]:
    interactions: List[Interaction] = runner.resolve_interactions(scenario)
    return [
        runner.interaction_loader.render_bot_turn(interaction.bot)
        for interaction in interactions
    ]
