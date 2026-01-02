import flet as ft

from atrament.components.previouse_projects_list import PreviouseProjectList
from atrament.components.starter_page import StarterPage
from atrament.page_ref import get_page_ref
from atrament.sections.section import Section


class HomeSection(Section):
    _route: str = "/"

    @staticmethod
    def route() -> str:
        return HomeSection._route

    def render(self) -> ft.View:
        window_height = get_page_ref().window.height

        return ft.View(
            route=self._route,
            controls=[
                ft.Row(
                    [
                        PreviouseProjectList(height=window_height),
                        StarterPage(height=window_height),
                    ]
                )
            ],
        )
