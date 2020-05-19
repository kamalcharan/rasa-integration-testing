import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

INTERACTIONS_FOLDER = "interactions"
INTERACTION_TURN_EXTENSION = "jinja"
USER_FOLDER = "user"
BOT_FOLDER = "bot"
NO_SUFFIX = ""


class InteractionTurn:
    def __init__(self, template: str, variables: dict = None):
        self._template = template
        self._variables = {} if variables is None else variables

    @property
    def template(self) -> str:
        return self._template

    @property
    def variables(self) -> dict:
        return self._variables

    def __repr__(self):
        return f"InteractionTurn: template={self.template}, variables={self.variables}"

    def __eq__(self, other) -> bool:
        return (
            self.__class__ == other.__class__
            and self.template == other.template
            and self.variables == other.variables
        )

    def __hash__(self):
        return hash((self.template, self.variables))


class Interaction:
    def __init__(self, user: InteractionTurn, bot: InteractionTurn):
        self._user = user
        self._bot = bot

    @property
    def user(self) -> InteractionTurn:
        return self._user

    @property
    def bot(self) -> InteractionTurn:
        return self._bot

    def __repr__(self):
        return f"Interaction: user={self.user} -> bot={self.bot}"

    def __eq__(self, other) -> bool:
        return (
            self.__class__ == other.__class__
            and self.user == other.user
            and self.bot == other.bot
        )

    def __hash__(self):
        return hash((self.user, self.bot))


class InteractionLoader:
    def __init__(self, test_definitions_path: Path):
        interactions_path = test_definitions_path.joinpath(INTERACTIONS_FOLDER)
        self._template_environment = Environment(
            loader=FileSystemLoader(str(interactions_path)),
            autoescape=select_autoescape(["json"]),
        )

    def render_user_turn(
        self, user_turn: InteractionTurn, env_variables: dict = {}
    ) -> dict:
        return self._render_turn(user_turn, USER_FOLDER, env_variables)

    def render_bot_turn(
        self, bot_turn: InteractionTurn, env_variables: dict = {}
    ) -> dict:
        return self._render_turn(bot_turn, BOT_FOLDER, env_variables)

    def _render_turn(
        self, turn: InteractionTurn, folder: str, env_variables: dict = {}
    ) -> dict:
        template_filename = f"{folder}/{turn.template}.{INTERACTION_TURN_EXTENSION}"
        template = self._template_environment.get_template(template_filename)
        rendered_template: str = template.render(**turn.variables, **env_variables)
        return json.loads(rendered_template)
