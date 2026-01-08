import asyncio
import difflib
import json
import os
import webbrowser
from enum import Enum
from pathlib import Path

import aiofiles
import flet as ft

from atrament import ai
from atrament.const import USER_DATA_PATH
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
            height=100,
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
                        f"{x[0].value}:{x[1]}",
                        leading_icon=x[0].to_icon(),
                        text=x[1],
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
            if f.path is None:
                continue

            # check if file is atrament.json we dont want to modify our own project files
            if f.name == "atrament.json":
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

            file_name = Path(p).name
            if len(file_name) > 25:
                file_name = file_name[:22] + "..."

            row = ft.Row(
                controls=[
                    ft.Text(file_name, size=16, margin=ft.Margin.only(left=10)),
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

    async def load_files_content(self, file_paths: list[str]) -> dict[str, str]:
        result = {}

        for p in file_paths:
            async with aiofiles.open(p, mode="r") as f:
                content = await f.read()
                result[p] = content

        return result

    async def backup_files(self, files: dict[str, str]) -> None:
        backup_dir_path = USER_DATA_PATH / "projects" / self.project_name

        # Clear the backup directory if it exists
        if backup_dir_path.exists():
            import shutil

            shutil.rmtree(backup_dir_path)
        backup_dir_path.mkdir(parents=True, exist_ok=True)

        async def backup_file(p: str, content: str) -> None:
            relative_file_path = Path(p).relative_to(self.path_to_project)
            backup_file_path = backup_dir_path / relative_file_path

            backup_file_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(backup_file_path, mode="w") as f:
                await f.write(content)

        tasks = [backup_file(p, content) for p, content in files.items()]
        await asyncio.gather(*tasks)

    async def prompt_ai(
        self, target_files: dict[str, str], source_files: dict[str, str]
    ) -> str:
        prompt = f"""You are an AI assistant that modifies files based on user instructions.

        INPUT STRUCTURE:
        - target_files: Files to be edited (provided as JSON)
        - source_files: Reference files that may contain relevant information (provided as JSON)
        - user_instructions: Specific editing instructions to apply

        USER INSTRUCTIONS:
        {self.config.instruction_field.value}

        TARGET FILES:
        {json.dumps(target_files, indent=2)}

        SOURCE FILES:
        {json.dumps(source_files, indent=2)}

        OUTPUT REQUIREMENTS:
        Return ONLY a valid JSON object with the same structure as target_files, containing the updated file contents.
        - Use proper JSON formatting with correctly escaped newlines (use \\n for line breaks, not literal backslash-n)
        - When the JSON is parsed by Python's json.loads(), the \\n sequences should become actual newline characters
        - Do not double-escape newlines (do not use \\\\n)
        - Do not include any explanations, greetings, or additional text outside the JSON
        - The response must be valid JSON that can be parsed directly

        Example: {{"file.txt": "first line\\nsecond line\\nthird line"}} will correctly produce newlines when parsed."""

        model_selection = (
            self.config.model_dropdown.value
        )  # format of this is "{AiCompany.value}:{model}"
        if model_selection is None:
            self.config.model_dropdown.error_text = "You need to select a model"
            raise ValueError("You need to select a model")

        company, model = model_selection.split(":")
        company = ai.AiCompany(int(company))

        try:
            return await ai.client.prompt(company, prompt, model)
        except Exception as e:
            raise e

    async def apply_response(self, response: str) -> None:
        output_files = json.loads(response)

        async def save_file(file_path: str, contents: str) -> None:
            async with aiofiles.open(file_path, "w") as file:
                await file.write(contents)

        tasks = [
            save_file(file_path, content)
            for file_path, content in output_files.items()
        ]
        await asyncio.gather(*tasks)

    async def see_change_report(self, _) -> None:
        backup_dir_path = USER_DATA_PATH / "projects" / self.project_name
        report_dir = USER_DATA_PATH / "reports" / self.project_name

        # Create reports directory
        os.makedirs(report_dir, exist_ok=True)

        new_file_paths = self.target_files.files
        backup_file_paths = list(
            map(
                lambda x: str(
                    backup_dir_path / Path(x).relative_to(self.path_to_project)
                ),
                self.target_files.files,
            )
        )

        # Generate diff reports
        differ = difflib.HtmlDiff()
        diff_files = []

        for idx, (new_file_path, old_file_path) in enumerate(
            zip(new_file_paths, backup_file_paths)
        ):
            # Read file contents
            try:
                async with aiofiles.open(
                    old_file_path, "r", encoding="utf-8"
                ) as f:
                    old_lines = await f.readlines()
            except Exception:
                old_lines = ["(File did not exist in backup)\n"]

            try:
                async with aiofiles.open(
                    new_file_path, "r", encoding="utf-8"
                ) as f:
                    new_lines = await f.readlines()
            except Exception:
                new_lines = ["(File does not exist)\n"]

            # Generate diff HTML
            diff_html = differ.make_file(
                old_lines,
                new_lines,
                fromdesc=f"Old: {Path(new_file_path).name}",
                todesc=f"New: {Path(new_file_path).name}",
                context=True,
                numlines=3,
            )

            # Save individual diff file
            diff_filename = f"diff_{idx}_{Path(new_file_path).stem}.html"
            diff_path = report_dir / diff_filename

            with open(diff_path, "w", encoding="utf-8") as f:
                f.write(diff_html)

            diff_files.append((Path(new_file_path).name, diff_filename))

        # Generate index page
        index_html = [
            "<!DOCTYPE html>",
            "<html><head>",
            '<meta charset="utf-8">',
            f"<title>Diff Report - {self.project_name}</title>",
            "<style>",
            'body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; max-width: 900px; margin: 50px auto; padding: 20px; background: #f5f5f5; }',
            "h1 { color: #333; border-bottom: 3px solid #0066cc; padding-bottom: 10px; }",
            ".info { background: white; padding: 15px; border-radius: 5px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }",
            "ul { list-style: none; padding: 0; }",
            "li { margin: 10px 0; background: white; padding: 15px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); transition: transform 0.2s; }",
            "li:hover { transform: translateX(5px); }",
            "a { text-decoration: none; color: #0066cc; font-size: 1.1em; font-weight: 500; }",
            "a:hover { text-decoration: underline; }",
            ".count { color: #666; font-size: 0.9em; margin-top: 10px; }",
            "</style>",
            "</head><body>",
            f"<h1>File Comparison Report: {self.project_name}</h1>",
            f'<div class="info"><strong>Total files compared:</strong> {len(diff_files)}</div>',
            "<ul>",
        ]

        for file_name, diff_file in diff_files:
            index_html.append(
                f'<li><a href="{diff_file}">📄 {file_name}</a></li>'
            )

        index_html.extend(["</ul>", "</body></html>"])

        # Write index file
        index_path = report_dir / "index.html"
        with open(index_path, "w", encoding="utf-8") as f:
            f.write("\n".join(index_html))

        # Open in browser
        webbrowser.open(f"file://{os.path.abspath(index_path)}")

    async def process_files(self, e):
        # Placeholder logic
        e.control.content = "Processing..."
        e.control.bgcolor = ft.Colors.ORANGE
        e.control.update()

        # ----- FUNCTION LIST ----- #
        # load content's of target and source files
        # make a backup at a specific location
        # make a prompt to LLM with our request
        # parse a response for new file content's
        # push a popup that transition's the user to a window where they can view the changes

        target_files = await self.load_files_content(self.target_files.files)
        source_files = await self.load_files_content(self.source_files.files)

        await self.backup_files(target_files)

        try:
            response = await self.prompt_ai(target_files, source_files)
        except Exception as e:
            get_page_ref().show_dialog(
                ft.AlertDialog(
                    title="Fetching Response problem",
                    content=ft.Text(f"error: {e}"),
                    actions=[
                        ft.TextButton(
                            "Dismiss",
                            on_click=lambda _: get_page_ref().pop_dialog(),
                        )
                    ],
                )
            )

            return

        await self.apply_response(response)

        e.control.content = "Done!"
        e.control.bgcolor = ft.Colors.GREEN
        e.control.update()

        get_page_ref().show_dialog(
            ft.AlertDialog(
                title="Job done",
                content=ft.Text(
                    "The task is done you can check the change report."
                ),
                actions=[
                    ft.TextButton(
                        "Check Report", on_click=self.see_change_report
                    ),
                    ft.TextButton(
                        "Dismiss",
                        on_click=lambda _: get_page_ref().pop_dialog(),
                    ),
                ],
            )
        )

        await asyncio.sleep(0.5)

        e.control.content = "Process Files"
        e.control.bgcolor = ft.Colors.BLUE
        e.control.update()

        # Enable rollback button after processing
        self.rollback_button.disabled = False
        self.rollback_button.bgcolor = ft.Colors.RED
        self.rollback_button.update()

    def is_there_available_backup(self) -> bool:
        backup_dir_path = USER_DATA_PATH / "projects" / self.project_name

        # Check if backup directory exists and has files
        if not backup_dir_path.exists():
            return False

        # Check if there are any backup files
        return any(backup_dir_path.iterdir())

    async def rollback_files(self, e):
        async def perform_rollback(_):
            get_page_ref().pop_dialog()

            backup_dir_path = USER_DATA_PATH / "projects" / self.project_name

            # Restore each file from backup
            for backup_file_path in backup_dir_path.rglob("*"):
                if backup_file_path.is_file():
                    relative_path = backup_file_path.relative_to(
                        backup_dir_path
                    )
                    original_file_path = self.path_to_project / relative_path

                    # Read backup content
                    async with aiofiles.open(backup_file_path, "r") as f:
                        content = await f.read()

                    # Write to original location
                    async with aiofiles.open(original_file_path, "w") as f:
                        await f.write(content)

            # Delete backup directory after successful rollback
            import shutil

            shutil.rmtree(backup_dir_path)

            # Disable rollback button
            self.rollback_button.disabled = True
            self.rollback_button.bgcolor = ft.Colors.with_opacity(
                0.5, ft.Colors.RED
            )
            self.rollback_button.update()

            # Show success message
            get_page_ref().show_dialog(
                ft.AlertDialog(
                    title="Rollback Complete",
                    content=ft.Text(
                        "Files have been successfully restored to their previous state."
                    ),
                    actions=[
                        ft.TextButton(
                            "OK",
                            on_click=lambda _: get_page_ref().pop_dialog(),
                        )
                    ],
                )
            )

        async def cancel_rollback(_):
            get_page_ref().pop_dialog()

        # Show confirmation dialog with options
        get_page_ref().show_dialog(
            ft.AlertDialog(
                title="Confirm Rollback",
                content=ft.Text(
                    "Are you sure you want to rollback all files to their previous state? "
                    "This will undo all changes made during the last processing."
                ),
                actions=[
                    ft.TextButton(
                        "See Change Report",
                        on_click=self.see_change_report,
                    ),
                    ft.TextButton(
                        "Rollback",
                        on_click=perform_rollback,
                    ),
                    ft.TextButton(
                        "Cancel",
                        on_click=cancel_rollback,
                    ),
                ],
            )
        )

    def render(self):
        self.process_button = ft.Button(
            "Process Files",
            icon=ft.Icons.PLAY_ARROW,
            bgcolor=ft.Colors.BLUE,
            color=ft.Colors.WHITE,
            height=50,
            on_click=self.process_files,
        )

        has_backup = self.is_there_available_backup()
        self.rollback_button = ft.Button(
            "Rollback",
            icon=ft.Icons.BACKUP,
            bgcolor=ft.Colors.RED
            if has_backup
            else ft.Colors.with_opacity(0.5, ft.Colors.RED),
            color=ft.Colors.WHITE,
            height=50,
            on_click=self.rollback_files,
            disabled=not has_backup,
        )

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
                                    ft.Column(
                                        [
                                            ft.Container(
                                                content=self.rollback_button,
                                                padding=ft.Padding.only(
                                                    left=20
                                                ),
                                                alignment=ft.Alignment.CENTER,
                                            ),
                                            ft.Container(
                                                content=self.process_button,
                                                padding=ft.Padding.only(
                                                    left=20
                                                ),
                                                alignment=ft.Alignment.CENTER,
                                            ),
                                        ]
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
