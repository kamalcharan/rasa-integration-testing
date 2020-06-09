import os
from asyncio import Condition, TimeoutError, wait_for
from typing import Any, List, Optional, Tuple

from socketio import AsyncClient, AsyncClientNamespace

from .common.configuration import configure
from .comparator import JsonDataComparator
from .interaction import Interaction, InteractionLoader
from .runner import FailedInteraction, ScenarioRunner
from .scenario import Scenario, ScenarioFragmentLoader

SESSION_ID_KEY = "session_id"
EVENT_BOT_UTTERED = "bot_uttered"
EVENT_USER_UTTERED = "user_uttered"
ENV_BOT_RESPONSE_TIMEOUT = "BOT_RESPONSE_TIMEOUT"

BOT_RESPONSE_TIMEOUT = float(os.environ.get(ENV_BOT_RESPONSE_TIMEOUT, 6.0))
IS_USER_MESSAGE = True
IS_BOT_MESSAGE = False


@configure(
    "protocol.url", InteractionLoader, ScenarioFragmentLoader, JsonDataComparator
)
class SocketIORunner(ScenarioRunner):
    async def run(self, scenario: Scenario) -> Optional[FailedInteraction]:
        client: AsyncClient = AsyncClient()

        interactions: List[Interaction] = self.resolve_interactions(scenario)
        runner_namespace = SocketIORunnerClientNamespace(
            self, interactions.copy(), dict(os.environ)
        )

        client.register_namespace(runner_namespace)

        # have to force polling or else python-socketio tries to close
        # non-existant websockets which produces warning logs.
        await client.connect(self.url, transports="polling")
        result = await runner_namespace.run()
        await client.disconnect()

        return result


class SocketIORunnerClientNamespace(AsyncClientNamespace):
    def __init__(
        self,
        socketio_runner: SocketIORunner,
        interactions: List[Interaction],
        substitutes: dict = {},
    ):
        super().__init__()
        self.socketio_runner = socketio_runner
        self._interaction_stack: List[Tuple[bool, dict]] = _create_interaction_stack(
            socketio_runner.interaction_loader, interactions, substitutes
        )
        self._timeout_condition = Condition()
        self._failed_interaction: Optional[FailedInteraction] = None
        self._current_user_input: dict = {}

    async def session_request(self) -> None:
        await self.emit("session_request")

    async def on_bot_uttered(self, data: Any) -> None:
        await self._timeout_notify()

        is_user_message, message = self._pop_interaction_stack()

        while is_user_message:
            await self._send_user_input(message)
            is_user_message, message = self._pop_interaction_stack()

        json_diff = self.socketio_runner.comparator.compare(message, data)

        if not json_diff.identical and self._failed_interaction is None:
            self._failed_interaction = FailedInteraction(
                self._current_user_input, message, data, json_diff,
            )

        if self._next_is_user_message():
            _, message = self._pop_interaction_stack()
            await self._send_user_input(message)

    def _next_is_user_message(self) -> bool:
        if len(self._interaction_stack) > 0:
            is_user_message, _ = self._interaction_stack[0]
            return is_user_message
        return False

    def _pop_interaction_stack(self) -> Tuple[bool, dict]:
        return (
            self._interaction_stack.pop(0)
            if len(self._interaction_stack) > 0
            else (False, {})
        )

    def _get_remaining_bot_messages(self) -> List[dict]:
        return [
            message
            for is_user_input, message in self._interaction_stack
            if not is_user_input
        ]

    async def _timeout_notify(self):
        async with self._timeout_condition:
            self._timeout_condition.notify()

    async def _timeout_await(self):
        async with self._timeout_condition:
            await self._timeout_condition.wait()

    async def _send_user_input(self, message: dict) -> None:
        await self._timeout_notify()
        self._current_user_input = {SESSION_ID_KEY: self.client.sid}
        self._current_user_input.update(message)
        await self.emit(EVENT_USER_UTTERED, self._current_user_input)

    async def run(self) -> Optional[FailedInteraction]:
        await self.session_request()

        is_user_input, message = self._pop_interaction_stack()
        if is_user_input:
            await self._send_user_input(message)

        try:
            while self._failed_interaction is None:
                await wait_for(
                    self._timeout_await(), timeout=BOT_RESPONSE_TIMEOUT,
                )
        except TimeoutError:
            remaining_messages = self._get_remaining_bot_messages()
            json_diff = self.socketio_runner.comparator.compare({}, remaining_messages)

            if not json_diff.identical and self._failed_interaction is None:
                return FailedInteraction(
                    self._current_user_input, {}, remaining_messages, json_diff,
                )

        return self._failed_interaction


def _create_interaction_stack(
    interaction_loader: InteractionLoader,
    interactions: List[Interaction],
    substitutes: dict,
) -> List[Tuple[bool, dict]]:
    rendered_messages: List[Tuple[bool, dict]] = []

    for interaction in interactions:
        rendered_messages.append(
            (
                IS_USER_MESSAGE,
                interaction_loader.render_user_turn(interaction.user, substitutes),
            )
        )
        rendered_bot_message = interaction_loader.render_bot_turn(
            interaction.bot, substitutes
        )

        for message in _split_rendered_messages(rendered_bot_message):
            rendered_messages.append((IS_BOT_MESSAGE, message))

    return rendered_messages


def _split_rendered_messages(rendered_message: dict) -> List[dict]:
    messages: List[dict] = []

    for message in rendered_message:
        messages.append(message)

    return messages
