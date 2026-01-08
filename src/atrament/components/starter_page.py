import datetime
import json
from pathlib import Path
from urllib.parse import quote

import aiofiles
import flet as ft

from atrament.const import PROJECT_TRACKER_FILE, PROJECT_TRACKER_LOCK
from atrament.page_ref import get_page_ref


def get_version() -> str:
    return "0.1.0"


async def create_project(_) -> None:
    directory_path = await ft.FilePicker().get_directory_path(
        dialog_title="Select Project Directory",
        initial_directory=str(Path.home()),
    )

    if directory_path is not None:
        await get_page_ref().push_route(
            f"/create_project/{quote(directory_path, safe='')}"
        )


async def open_project() -> None:
    atrament_file = (
        await ft.FilePicker().pick_files(
            dialog_title="Find atrament project file",
            initial_directory=str(Path.home()),
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["json"],
            allow_multiple=False,
        )
    )[0]

    if atrament_file.path is None:
        return

    project_path = Path(atrament_file.path).parent

    # check if it is a valid atrament.json
    if not Path(atrament_file.path).name == "atrament.json":
        return

    with open(atrament_file.path, "r") as f:
        project_data = json.load(f)
        safe_name = project_data["metadata"]["name"]

    today = datetime.date.today().strftime("%Y-%m-%d")

    entry = f"{safe_name}, {today}, {project_path}\n"
    # Ensure parent dir exists
    PROJECT_TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)

    with PROJECT_TRACKER_LOCK:
        async with aiofiles.open(
            PROJECT_TRACKER_FILE, "a", encoding="utf-8"
        ) as f:
            await f.write(entry)

    await get_page_ref().push_route(
        f"/project/{quote(str(project_path), safe='')}"
    )


async def settings() -> None:
    await get_page_ref().push_route("/settings/")


@ft.control
class StarterPageAction(ft.Row):
    label: str = ""
    quick_description: str = ""
    button_text: str = ""

    def __init__(self, button_action=None, **kwargs):
        # 1. We extract our non-serializable 'button_action'
        self.button_action = button_action

        # 2. "Pop" the hinted fields out of kwargs so ft.Row doesn't see them.
        # This prevents the "unexpected keyword argument" error.
        self.label = kwargs.pop("label", "")
        self.quick_description = kwargs.pop("quick_description", "")
        self.button_text = kwargs.pop("button_text", "")

        # 2. We pass everything else (label, etc.) to the Flet/Decorator machinery
        super().__init__(**kwargs)

    def init(self):
        self.height = 30
        self.align = ft.Alignment.CENTER
        self.width = 500
        self.alignment = ft.MainAxisAlignment.SPACE_BETWEEN
        self.margin = ft.Margin.all(10)

        self.action_descrition = ft.Column(
            controls=[
                ft.Text(
                    self.label,
                    size=17,
                    color=ft.Colors.WHITE,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Text(
                    self.quick_description, size=10, color=ft.Colors.GREY_100
                ),
            ],
            align=ft.Alignment.CENTER,
            width=350,
        )

        self.controls = [
            self.action_descrition,
            ft.Button(
                self.button_text,
                bgcolor=ft.Colors.BLUE,
                color=ft.Colors.WHITE,
                on_click=self.button_action,
                align=ft.Alignment.CENTER,
            ),
        ]


@ft.control
class StarterPage(ft.Container):
    def init(self):
        self.alignment = ft.Alignment.CENTER
        self.align = ft.Alignment.CENTER_RIGHT
        self.bgcolor = ft.Colors.BLACK_12
        self.expand = True

        self.title = ft.Text(
            "Atrament",
            size=35,
            color=ft.Colors.BLUE,
            weight=ft.FontWeight.BOLD,
            align=ft.Alignment.CENTER,
        )

        self.version_text = ft.Text(
            f"Version: {get_version()}",
            size=15,
            color=ft.Colors.GREY_400,
            weight=ft.FontWeight.W_400,
            align=ft.Alignment.CENTER,
        )

        self.content = ft.Column(
            [
                ft.Column(
                    [self.title, self.version_text],
                    margin=ft.Margin.only(top=80, bottom=80),
                ),
                StarterPageAction(
                    label="Create Project",
                    quick_description="Create a new Atrament project to fix and improve your documents",
                    button_text="Create",
                    button_action=create_project,
                ),
                ft.Divider(),
                StarterPageAction(
                    label="Open Project",
                    quick_description="Open an existing Atrament Project",
                    button_text="Open",
                    button_action=open_project,
                ),
                ft.Divider(),
                ft.Container(
                    expand=True,
                    content=ft.IconButton(
                        ft.Icons.SETTINGS,
                        on_click=settings,
                    ),
                    alignment=ft.Alignment.BOTTOM_RIGHT,
                    padding=ft.Padding.only(
                        right=10, left=10, top=50, bottom=50
                    ),
                ),
            ]
        )
