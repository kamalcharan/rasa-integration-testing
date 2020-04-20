import json
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, Optional

from aiohttp import ClientResponse, ClientSession, ContentTypeError

from .configuration import configure


class ProtocolException(Exception):
    pass


class Protocol(ABC):
    def __init__(self, url: str):
        self._url = url

    async def _post(self, data: Any, session: ClientSession) -> dict:
        response: ClientResponse = await session.post(self._url, data=data)
        try:
            return await response.json()
        except ContentTypeError as error:
            message = await response.text()
            raise ProtocolException(f"{error}, server response received: {message}")

    @abstractmethod
    async def send_input(self, input: Any, session: ClientSession) -> Any:
        pass


class RestChannelProtocol(Protocol):
    def __init__(self, url: str):
        super().__init__(url)

    async def send_input(self, json_input: dict, session: ClientSession) -> dict:
        response = await self._post(json.dumps(json_input), session)
        return response


class TestChannelProtocol(Protocol):
    def __init__(self, url: str):
        super().__init__(url)

    async def send_input(
        self, test_input: dict, session: Optional[ClientSession]
    ) -> dict:
        if session is None:
            raise ProtocolException()
        return test_input


class ProtocolType(Enum):
    VOICEXML = ("rest", RestChannelProtocol)
    TEST = ("test", TestChannelProtocol)

    def __init__(self, key: str, protocol_constructor: Callable):
        self.key = key
        self.protocol_constructor = protocol_constructor

    @classmethod
    def to_dict(cls) -> Dict[str, Callable]:
        return {entry.key: entry.protocol_constructor for entry in cls}

    @classmethod
    def from_string(cls, protocol_type: str, url) -> Protocol:
        selector_callables: Dict[str, Callable] = cls.to_dict()
        if protocol_type in selector_callables:
            return selector_callables[protocol_type](url)

        raise Exception(f"'{protocol_type}' isn't a valid protocol type.")


@configure("protocol.type", "protocol.url")
def protocol_selector(protocol_type: str, url: str) -> Protocol:
    return ProtocolType.from_string(protocol_type, url)
