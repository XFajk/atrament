import asyncio
import json
from enum import Enum
from pathlib import Path

import flet as ft

from atrament import ai
from atrament.page_ref import get_page_ref
from atrament.sections.section import Section


def save_project_data(data: dict, project_file: Path) -> None:
    with open(project_file, "w") as f:
        json.dump(data, f, indent=2)


@ft.control
class ProjectHeader(ft.Row):
    project_name: str = ""

    def __init__(self, project_path: Path, project_data: dict = {}, **kwargs):
        self.project_data = project_data
        self.project_path = project_path

        self.project_name = kwargs.pop("project_name", "")

        super().__init__(**kwargs)

    def init(self):
        self.alignment = ft.MainAxisAlignment.SPACE_BETWEEN
        self.vertical_alignment = ft.CrossAxisAlignment.CENTER
        self.controls = [
            ft.Row(
                [
                    ft.IconButton(ft.Icons.ARROW_BACK, on_click=self.go_back),
                    ft.Text(
                        self.project_name,
                        size=25,
                        weight=ft.FontWeight.BOLD,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.IconButton(ft.Icons.SETTINGS, on_click=self.go_settings),
        ]

    async def go_back(self, _):
        save_project_data(
            self.project_data, self.project_path / "atrament.json"
        )
        page = get_page_ref()
        if len(page.views) > 1:
            page.views.pop()
            top_route = page.views[-1].route
            if top_route is not None and top_route.startswith(
                "/create_project/"
            ):
                page.views.pop()
                top_route = page.views[-1].route

            await page.push_route(top_route or "/")
        else:
            page.update()

    async def go_settings(self, _):
        await get_page_ref().push_route("/settings/")


@ft.control
class ProjectConfiguration(ft.Column):
    def __init__(self, project_path: Path, project_data: dict = {}, **kwargs):
        self.project_path = project_path
        self.project_data = project_data
        super().__init__(**kwargs)

    def on_prompt_change(self, e):
        self.project_data["workdata"]["ai-configuration"]["prompt"] = (
            e.control.value
        )
        save_project_data(
            self.project_data, self.project_path / "atrament.json"
        )

    def on_model_select(self, e):
        self.project_data["workdata"]["ai-configuration"]["model"] = (
            e.control.value
        )
        save_project_data(
            self.project_data, self.project_path / "atrament.json"
        )

    def init(self):
        self.expand = True
        self.instruction_field = ft.TextField(
            label="Instructions",
            value=self.project_data["workdata"]["ai-configuration"]["prompt"],
            multiline=True,
            min_lines=3,
            max_lines=5,
            border_color=ft.Colors.BLUE_200,
            width=550,
            on_change=self.on_prompt_change,
        )

        # Start with empty dropdown - will be populated in did_mount
        self.model_dropdown = ft.Dropdown(
            label="Select Model",
            options=[],
            value=self.project_data["workdata"]["ai-configuration"]["model"],
            menu_height=200,
            border_color=ft.Colors.BLUE_200,
            on_select=self.on_model_select,
        )

        self.controls = [
            ft.Text("Configuration", size=18, weight=ft.FontWeight.BOLD),
            self.instruction_field,
            self.model_dropdown,
        ]

    def did_mount(self):
        # Load models asynchronously after component is mounted
        async def load_models():
            models = await ai.get_models()
            options = list(
                map(
                    lambda x: ft.DropdownOption(
                        x[1], leading_icon=x[0].to_icon()
                    ),
                    models,
                )
            )
            self.model_dropdown.options = options
            self.model_dropdown.update()

        # Create task to run async function
        asyncio.create_task(load_models())


class FileType(Enum):
    Source = "source-files"
    Target = "target-files"


@ft.control
class FileList(ft.Column):
    title: str = ""
    initial_directory: str = ""

    def __init__(
        self,
        filetype: FileType,
        project_path: Path,
        project_data: dict = {},
        **kwargs,
    ):
        self.project_path = project_path
        self.project_data = project_data
        self.filetype = filetype

        self.title = kwargs.pop("title", "")
        self.initial_directory = kwargs.pop("initial_directory", "")

        super().__init__(**kwargs)

    def init(self):
        self.expand = True
        self.files: list[str] = self.project_data["workdata"]["files"][
            self.filetype.value
        ]

        self.file_list_view = ft.ListView(
            expand=True, spacing=5, padding=5, height=140
        )
        self.search_field = ft.TextField(
            hint_text="Search...",
            height=30,
            text_size=12,
            content_padding=10,
            on_change=self.update_list,
            border_color=ft.Colors.BLUE_200,
        )

        self.controls = [
            ft.Row(
                [
                    ft.Text(self.title, weight=ft.FontWeight.BOLD),
                    ft.Button(
                        "Select Files",
                        icon=ft.Icons.ADD,
                        on_click=self.pick_files,
                        height=30,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Container(
                content=self.file_list_view,
                bgcolor=ft.Colors.BLACK_12,
                border_radius=5,
                padding=10,
                expand=True,
            ),
            self.search_field,
        ]

    def did_mount(self):
        self.update_list()

    async def pick_files(self, _):
        result = await ft.FilePicker().pick_files(
            allow_multiple=True, initial_directory=self.initial_directory
        )

        for f in result:
            # Check if file is under project path
            if f.path is None:
                continue

            # Check if file is under project path we dont want random files
            try:
                file_path = Path(f.path).resolve()
                project_path = self.project_path.resolve()
                # Check if the file is relative to the project path
                file_path.relative_to(project_path)
            except (ValueError, OSError):
                # File is not under project path, skip it
                continue

            if f.path not in self.files:
                self.files.append(f.path)
            self.update_list()

    def remove_file(self, file_path: str):
        if file_path in self.files:
            self.files.remove(file_path)
            self.update_list()

    def _make_delete_handler(self, file_path: str):
        def handler(e):
            self.remove_file(file_path)

        return handler

    def update_list(self, _=None):
        search_filter = (self.search_field.value or "").lower()
        self.file_list_view.controls = []

        for p in self.files:
            if search_filter and search_filter not in Path(p).name.lower():
                continue

            row = ft.Row(
                controls=[
                    ft.Text(
                        Path(p).name, size=16, margin=ft.Margin.only(left=10)
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE,
                        icon_color=ft.Colors.RED,
                        on_click=self._make_delete_handler(str(p)),
                        margin=ft.Margin.only(right=10),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
            self.file_list_view.controls.append(row)

        if search_filter:
            self.project_data["workdata"]["files"][self.filetype.value] = (
                self.files
            )
            save_project_data(
                self.project_data, self.project_path / "atrament.json"
            )

        self.file_list_view.update()


class ProjectSection(Section):
    _route: str = "/project/:encoded_path"

    def __init__(self, path_to_project: str):
        self.path_to_project = Path(path_to_project)
        self.project_name = self.path_to_project.name
        self.project_data: dict = {}

        # Try to load project name from atrament.json
        try:
            config_path = self.path_to_project / "atrament.json"
            if config_path.exists():
                with open(config_path, "r") as f:
                    data = json.load(f)
                    self.project_data = data
                    if "metadata" in data and "name" in data["metadata"]:
                        self.project_name = data["metadata"]["name"]
        except Exception:
            pass

        # Components
        self.header = ProjectHeader(
            self.path_to_project,
            project_name=self.project_name,
            project_data=self.project_data,
        )
        self.config = ProjectConfiguration(
            self.path_to_project, project_data=self.project_data
        )
        self.target_files = FileList(
            FileType.Target,
            self.path_to_project,
            project_data=self.project_data,
            title="Files to Edit",
            initial_directory=str(self.path_to_project),
        )
        self.source_files = FileList(
            FileType.Source,
            self.path_to_project,
            project_data=self.project_data,
            title="Source Files",
            initial_directory=str(self.path_to_project),
        )

    @staticmethod
    def route() -> str:
        return ProjectSection._route

    async def process_files(self, e):
        # Placeholder logic
        e.control.content = "Processing..."
        e.control.bgcolor = ft.Colors.ORANGE
        e.control.update()

        e.control.content = "Done!"
        e.control.bgcolor = ft.Colors.GREEN
        e.control.update()

        await asyncio.sleep(0.5)

        e.control.content = "Process Files"
        e.control.bgcolor = ft.Colors.BLUE
        e.control.update()

    def render(self):
        return ft.View(
            route=self._route,
            controls=[
                ft.Container(
                    padding=20,
                    content=ft.Column(
                        controls=[
                            self.header,
                            ft.Divider(),
                            # Config & Process
                            ft.Row(
                                [
                                    self.config,
                                    ft.Container(
                                        content=ft.Button(
                                            "Process Files",
                                            icon=ft.Icons.PLAY_ARROW,
                                            bgcolor=ft.Colors.BLUE,
                                            color=ft.Colors.WHITE,
                                            height=50,
                                            on_click=self.process_files,
                                        ),
                                        padding=ft.Padding.only(left=20),
                                        alignment=ft.Alignment.CENTER,
                                    ),
                                ],
                                vertical_alignment=ft.CrossAxisAlignment.END,
                            ),
                            ft.Divider(),
                            # Files
                            ft.Row(
                                controls=[
                                    self.target_files,
                                    self.source_files,
                                ],
                                expand=True,
                            ),
                        ],
                        expand=True,
                    ),
                    expand=True,
                ),
            ],
        )
