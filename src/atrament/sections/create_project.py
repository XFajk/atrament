import datetime
import json
from pathlib import Path

import flet as ft

from atrament.const import PROJECT_TRACKER_FILE, PROJECT_TRACKER_LOCK
from atrament.page_ref import get_page_ref
from atrament.sections.section import Section


class CreateProjectSection(Section):
    _route: str = "/create_project/:encoded_path"

    def __init__(self, path_to_project: str):
        self.path_to_project = path_to_project
        self.name_field = ft.TextField(
            label="Project Name",
            autofocus=True,
            border_color=ft.Colors.GREY_400,
        )
        self.description_field = ft.TextField(
            label="*Description",
            multiline=True,
            min_lines=3,
            border_color=ft.Colors.GREY_400,
        )

    @staticmethod
    def route() -> str:
        return CreateProjectSection._route

    async def create_project(self, _):
        name = self.name_field.value
        if not name:
            self.name_field.error = "Name is required"
            self.name_field.update()
            return

        # Sanitize name (simple CSV protection)
        safe_name = name.replace(",", "")

        # Save project metadata
        project_dir = Path(self.path_to_project)
        project_dir.mkdir(parents=True, exist_ok=True)

        metadata = {
            "name": name,
            "description": self.description_field.value,
        }

        with open(project_dir / "atrament.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4)

        today = datetime.date.today().strftime("%Y-%m-%d")

        # Format: project_name, last_time_edited, project_dir
        entry = f"{safe_name}, {today}, {self.path_to_project}\n"

        # Ensure parent dir exists
        PROJECT_TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)

        with PROJECT_TRACKER_LOCK:
            with open(PROJECT_TRACKER_FILE, "a", encoding="utf-8") as f:
                f.write(entry)

        await get_page_ref().push_route("/project/:encoded_path")

    async def cancel(self, _):
        page = get_page_ref()
        if len(page.views) > 1:
            page.views.pop()
            top_view = page.views[-1]
            await page.push_route(top_view.route or "/")
        else:
            await page.push_route("/")

    def render(self):
        return ft.View(
            route=self._route,
            controls=[
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "Create New Project",
                                size=30,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                f"Location: {self.path_to_project}",
                                size=12,
                                color=ft.Colors.GREY,
                            ),
                            ft.Divider(),
                            self.name_field,
                            self.description_field,
                            ft.Row(
                                [
                                    ft.TextButton(
                                        "Cancel", on_click=self.cancel
                                    ),
                                    ft.Button(
                                        "Create Project",
                                        on_click=self.create_project,
                                        bgcolor=ft.Colors.BLUE,
                                        color=ft.Colors.WHITE,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.END,
                            ),
                        ],
                        width=600,
                        spacing=20,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=50,
                    expand=True,
                )
            ],
            vertical_alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
