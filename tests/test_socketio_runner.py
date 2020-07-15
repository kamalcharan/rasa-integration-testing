import asyncio
from pathlib import Path
from threading import Thread
from typing import Any, List
from unittest import TestCase

from aiohttp import web
from socketio import AsyncServer

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
        self.runner = self.aiohttp_server()
        Thread(target=self.run_server, args=(self.runner,), daemon=True).start()

    def test_identical(self):
        runner = _scenario_runner(SUCCESS_TESTS_PATH)
        scenario = Scenario.from_file("success", SUCCESS_SCENARIO_PATH)
        self.bot_messages_stack = _bot_message_stack(runner, scenario)

        result = runner.run(scenario)
        self.assertEqual(result, None)

    def aiohttp_server(self):
        sio = AsyncServer(async_mode="aiohttp")

        @sio.on(EVENT_USER_UTTERED)
        async def on_user_uttered(session_id: str, request: Any):
            if self.bot_messages_stack:
                messages = self.bot_messages_stack.pop(0)
                for message in messages:
                    await sio.emit(EVENT_BOT_UTTERED, message, room=session_id)

        app = web.Application()
        sio.attach(app)
        runner = web.AppRunner(app)
        return runner

    def run_server(self, runner: web.AppRunner):
        self.server_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.server_loop)
        self.server_loop.run_until_complete(runner.setup())
        self.site = web.TCPSite(runner, "localhost", 8080)
        self.server_loop.create_task(self.site.start())
        self.server_loop.run_forever()


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
