from abc import ABC, abstractmethod

import flet as ft


class Section(ABC):
    @staticmethod
    @abstractmethod
    def route() -> str: ...

    @abstractmethod
    def render(self) -> ft.View: ...
