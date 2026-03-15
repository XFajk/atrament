import flet as ft

from atrament.components.previouse_projects_list import PreviouseProjectList
from atrament.components.starter_page import StarterPage
from atrament.sections.section import Section


class HomeSection(Section):
    _route: str = "/"

    @staticmethod
    def route() -> str:
        return HomeSection._route

    def render(self) -> ft.View:
        return ft.View(
            route=self._route,
            controls=[
                ft.Row(
                    [
                        PreviouseProjectList(expand=True),
                        ft.VerticalDivider(width=1),
                        StarterPage(expand=True),
                    ],
                    expand=True,
                    spacing=0,
                )
            ],
        )
