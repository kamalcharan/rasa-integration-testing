from collections.abc import Iterable, Sequence
from itertools import chain
from typing import Iterable as TypeIterable
from typing import Sequence as TypeSequence
from typing import Union

from .common import lazy_property


class Identifier(Sequence):
    Elements = TypeSequence[str]
    ELEMENT_SEPARATOR: str = "."

    def __init__(self, *elements: str):
        self.elements = elements

    def __add__(self, other: TypeIterable[str]):
        if not isinstance(other, Iterable):
            raise NotImplementedError("Can only concatenate Identifier with iterables.")
        sequence = chain(self, other)
        return self.__class__(*sequence)

    def __getitem__(self, index: Union[int, slice]):
        return self.elements[index]

    def __len__(self) -> int:
        return len(self.elements)

    def __eq__(self, other) -> bool:
        return (
            self.__class__ == other.__class__
            and self.join_elements == other.join_elements
        )

    def __hash__(self) -> int:
        return hash(self.join_elements)

    def __str__(self) -> str:
        return self.join_elements

    def __repr__(self) -> str:
        return f"<{self.__class__}: '{self.join_elements}'>"

    @lazy_property
    def join_elements(self) -> str:
        return self.__class__.ELEMENT_SEPARATOR.join(self.elements)

    @classmethod
    def from_string(cls, string_identifier: str):
        return cls(*string_identifier.split(cls.ELEMENT_SEPARATOR))
