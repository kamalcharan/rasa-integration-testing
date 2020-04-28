import os
import re
from configparser import ConfigParser
from inspect import signature
from pathlib import Path
from typing import Any, Callable, Dict, Type, TypeVar, Union

CONFIGURE_OPTIONS_PATTERN = r"\s*(\w+)\.(\w+)\s*"
SECTION_CAPTURE = 1
OPTION_CAPTURE = 2
T = TypeVar("T")


class Configuration(ConfigParser):
    def __init__(self, configuration_path: Path):
        super().__init__(os.environ)
        with open(configuration_path, "r") as file:
            self.read_file(file)


class Configured:
    def __init__(self, constructor: Callable, *parameters, **key_parameters):
        self._constructor = constructor
        self._parameters = parameters
        self._key_parameters = key_parameters
        self.__name__ = constructor.__name__
        self.__doc__ = constructor.__doc__

    def __eq__(self, other):
        return (
            self.__class__ == other.__class__
            and self._constructor == other._constructor
        )

    def __hash__(self):
        return hash(self._constructor)

    def __call__(self, *args, **kwargs):
        return self._constructor(*args, **kwargs)

    @property
    def constructor(self) -> Callable:
        return self._constructor

    @property
    def parameters(self) -> tuple:
        return self._parameters

    @property
    def key_parameters(self) -> dict:
        return self._key_parameters


def configure(*parameters, **key_parameters) -> Callable:
    """
    Decorator for classes to map objects to configuration, default values or other
    configured objects.
    """

    def decorate(constructor: Callable) -> Configured:
        return Configured(constructor, *parameters, **key_parameters)

    return decorate


class DependencyInjector:
    """
    Keeps track of singleton configuration objects.
    """

    def __init__(self, configuration: ConfigParser):
        self._configuration = configuration
        self._wired_objects: Dict[Configured, Any] = {}

    def autowire(self, configured: Callable) -> T:
        """
        Pass configured object constructor, returns instance of object.
        """
        if isinstance(configured, Configured):
            if configured not in self._wired_objects:
                self._wired_objects[configured] = self._map_constructor(configured)
            return self._wired_objects[configured]
        raise Exception(
            f"Tried to autowire non-configured object {configured.__name__}"
        )

    def _map_constructor(self, configured: Configured) -> T:
        return configured.constructor(
            *self._resolve_parameters(configured),
            **self._resolve_keyword_parameters(configured),
        )

    def _resolve_parameters(self, configured: Configured):
        constructor = configured.constructor
        constructor_signature = signature(constructor)
        indexable_parameters = list(constructor_signature.parameters.values())
        if len(configured.parameters) > len(indexable_parameters):
            raise Exception(
                f"{configured.__name__} configure decorator has too many arguments"
            )
        return [
            self._resolve_argument(
                constructor, arg, indexable_parameters[index].annotation
            )
            for index, arg in enumerate(configured.parameters)
        ]

    def _resolve_keyword_parameters(self, configured: Configured):
        constructor = configured.constructor
        constructor_signature = signature(constructor)
        for key, arg in configured.key_parameters.items():
            if key not in constructor_signature.parameters:
                raise Exception(
                    f"{constructor.__name__} configure decorator got "
                    f"unexpected argument '{key}'"
                )

        return {
            key: self._resolve_argument(
                constructor, arg, constructor_signature.parameters[key].annotation
            )
            for key, arg in configured.key_parameters.items()
        }

    def _resolve_argument(
        self, constructor: Callable, argument: Any, annotation: Type
    ) -> Any:
        if isinstance(argument, str):
            return self._get_option(constructor, argument, annotation)
        if isinstance(argument, Configured):
            return self.autowire(argument)
        return argument

    def _get_option(
        self, constructor: Callable, option: str, annotation: Type
    ) -> Union[str, bool, float, int]:
        capture = re.match(CONFIGURE_OPTIONS_PATTERN, option)

        if not capture:
            raise Exception(
                f"Invalid configure decorator option: {option} from "
                f"{constructor.__name__} configure tag. Use the format section.option"
            )

        section_option = (capture[SECTION_CAPTURE], capture[OPTION_CAPTURE])
        if annotation is int:
            return self._configuration.getint(*section_option)
        if annotation is bool:
            return self._configuration.getboolean(*section_option)
        if annotation is float:
            return self._configuration.getfloat(*section_option)
        return self._configuration.get(*section_option)
