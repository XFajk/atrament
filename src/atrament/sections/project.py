import flet as ft

from atrament.sections.section import Section


class ProjectSection(Section):
    _route: str = "/project/:encoded_path"

    def __init__(self, path_to_project: str):
        pass

    @staticmethod
    def route() -> str:
        return ProjectSection._route

    def render(self):
        return ft.View(
            route=self._route, controls=[ft.Text("This is a project")]
        )
