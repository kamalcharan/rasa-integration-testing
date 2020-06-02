from itertools import zip_longest
from os import getpid
from socket import gethostname
from typing import Any, Callable, Iterable, Tuple, TypeVar

T = TypeVar("T")
TRACKER_ID_SIGNATURE = "ITEST"


def generate_tracker_id_from_scenario_name(
    run_timestamp: float, scenario_name: str
) -> str:
    unique_identifier = f"{gethostname()}{str(getpid())}_{run_timestamp}"
    return f"{TRACKER_ID_SIGNATURE}_{unique_identifier}_{scenario_name}"


def quick_chunk(chunkable: Tuple[T, ...], chunk_size: int) -> Iterable[Tuple[T, ...]]:
    return zip_longest(*[iter(chunkable)] * chunk_size)


# credits to Rasa, from rasa utils common
def lazy_property(function: Callable) -> Any:
    """Allows to avoid recomputing a property over and over.

    The result gets stored in a local var. Computation of the property
    will happen once, on the first call of the property. All
    succeeding calls will use the value stored in the private property."""

    attr_name = "_lazy_" + function.__name__

    @property  # type: ignore
    def _lazyprop(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, function(self))
        return getattr(self, attr_name)

    return _lazyprop
