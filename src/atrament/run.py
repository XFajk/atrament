import os
from urllib.parse import unquote

import flet as ft
import platformdirs

from atrament.page_ref import get_page_ref, set_page_ref
from atrament.sections.create_project import CreateProjectSection
from atrament.sections.home import HomeSection
from atrament.sections.project import ProjectSection
from atrament.sections.settings import SettingsSection

MAX_HISTORY: int = 3


def change_section(section_path: str, outside_routing: bool = False) -> None:
    """
    Params:
        section_path: str - The path of the section to change to.
        outside_routing: bool - Whether the change is being made outside of the routing system.
            Aka whenever this function is called outside of page.on_route_change callback this needs to be set to True
    """
    page_ref: ft.Page = get_page_ref()

    troute = ft.TemplateRoute(section_path)
    if page_ref.views[-1].route is not None:
        if troute.match(page_ref.views[-1].route) and not outside_routing:
            while len(page_ref.views) > MAX_HISTORY:
                page_ref.views.pop(0)

            page_ref.update()
            return

    if troute.match(HomeSection.route()):
        page_ref.views.append(HomeSection().render())
    elif troute.match(ProjectSection.route()):
        encoded = getattr(troute, "encoded_path", "")
        page_ref.views.append(ProjectSection(unquote(encoded)).render())
    elif troute.match(CreateProjectSection.route()):
        encoded = getattr(troute, "encoded_path", "")
        page_ref.views.append(CreateProjectSection(unquote(encoded)).render())
    elif troute.match(SettingsSection.route()):
        page_ref.views.append(SettingsSection().render())
    else:
        page_ref.views.append(
            ft.View(controls=[ft.Text("This URL dosent exist Error 404")])
        )

    while len(page_ref.views) > MAX_HISTORY:
        page_ref.views.pop(0)

    page_ref.update()


def setup_user() -> None:
    """Ensure the application's user data directory exists.

    Uses platformdirs.user_data_dir to determine the platform-appropriate
    location for user data and creates the directory if it does not exist.
    """
    user_data_dir = platformdirs.user_data_dir("Atrament")
    try:
        os.makedirs(user_data_dir, exist_ok=True)
    except Exception as e:
        print(f"Could not create user data directory '{user_data_dir}': {e}")


def main(page: ft.Page):
    setup_user()
    set_page_ref(page)
    page.window.height = 628.0
    page.window.width = 800.0

    page.title = "Atrament"

    page.window.resizable = False

    def route_change(e: ft.RouteChangeEvent) -> None:
        change_section(e.route)

    page.on_route_change = route_change
    change_section(page.route, True)


def run():
    ft.run(main)
