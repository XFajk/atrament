from enum import Enum
from sys import stderr

import flet as ft
import keyring
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

WANTED_OPENAI_MODELS = {
    "gpt-5-nano",
    "gpt-5-mini",
    "gpt-5",
    "gpt-4.1",
    "gpt-4o",
}

WANTED_ANTHROPIC_MODELS = {
    "claude-sonnet-4-5",
    "claude-haiku-4-5",
    "claude-opus-4-5",
}


class AiCompany(Enum):
    OpenAI = 0
    Anthropic = 1

    def to_icon(self) -> ft.Image:
        match self:
            case AiCompany.OpenAI:
                return ft.Image(
                    src="icons/openai_icon.svg", width=32, height=32
                )
            case AiCompany.Anthropic:
                return ft.Image(
                    src="icons/anthropic_icon.svg", width=32, height=32
                )
            case _:
                raise ValueError(f"Unknown company: {self}")


SUPPORTED_COMPANIES = {
    AiCompany.OpenAI,
    AiCompany.Anthropic,
}


class AiClinet:
    def __init__(self):
        self._client_store: dict[AiCompany, object] = {}

    def get_client(self, company: AiCompany) -> object | None:
        """
        MAINTENECE WARING: This function work's on the fact,
            that the API key's are stored behind a very specific name.
            So if  that was changed this is going to be the first place that need's refactor

        Returns async clients for making non-blocking API calls
        """
        client = None

        match company:
            case AiCompany.OpenAI:
                api_key = keyring.get_password("atrament", "ChatGPT:api-key")
                if api_key is None or api_key == "":
                    return None
                client = self._client_store.get(
                    company,
                    AsyncOpenAI(api_key=api_key),
                )
            case AiCompany.Anthropic:
                api_key = keyring.get_password("atrament", "Claude:api-key")
                if api_key is None or api_key == "":
                    return None
                client = self._client_store.get(
                    company,
                    AsyncAnthropic(api_key=api_key),
                )
            case _:
                print(
                    "ai.py::AiClient.get_client(): Currently unimplemented AI soruce",
                    file=stderr,
                )

        return client


client = AiClinet()


async def _get_openai_models() -> list[str]:
    result = []

    cl = client.get_client(AiCompany.OpenAI)
    if not isinstance(cl, AsyncOpenAI):
        raise ValueError("Invalid client type")

    models = await cl.models.list()
    for model in models.data:
        result.append(model.id)

    # filtering the result's for the model's we want
    result = list(filter(lambda x: x in WANTED_OPENAI_MODELS, result))

    return result


async def _get_anthropic_models():
    result = []

    cl = client.get_client(AiCompany.Anthropic)
    if not isinstance(cl, AsyncAnthropic):
        raise ValueError("Invalid client type")

    models = await cl.models.list()
    for model in models.data:
        result.append(model.id)

    # filtering the result's for the model's we want
    result = list(filter(lambda x: x in WANTED_ANTHROPIC_MODELS, result))

    return result


async def get_models() -> list[tuple[AiCompany, str]]:
    """
    Return a list of models that the user can use for the given keys
    Returns:
        list[tuple[AiCompany, str]]: A list of tuples containing available model's with information from where the model is
    """

    result: list[tuple[AiCompany, str]] = []

    for company in SUPPORTED_COMPANIES:
        match company:
            case AiCompany.OpenAI:
                try:
                    models = await _get_openai_models()
                    result.extend(map(lambda x: (company, x), models))
                except Exception as e:
                    print(f"Error fetching OpenAI models: {e}", file=stderr)
            case AiCompany.Anthropic:
                try:
                    models = await _get_anthropic_models()
                    result.extend(map(lambda x: (company, x), models))
                except Exception as e:
                    print(f"Error fetching Anthropic models: {e}", file=stderr)
            case _:
                print(
                    "ai.py::get_models(): Currently unimplemented AI soruce",
                    file=stderr,
                )

    return result
