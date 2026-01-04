import datetime
import json
from pathlib import Path
from urllib.parse import quote

import flet as ft

from ..const import PROJECT_TRACKER_FILE, PROJECT_TRACKER_LOCK
from ..page_ref import get_page_ref


@ft.control
class ProjectEntry(ft.Button):
    project_name: str = ""
    last_time_edited: datetime.date = datetime.date.today()
    project_path: str = "NOT A VALID PATH"

    async def open_project(self, _):
        """Route to the project section with the encoded project path."""
        encoded_path = quote(self.project_path, safe="")
        await get_page_ref().push_route(f"/project/{encoded_path}")

    async def delete_project(self, _):
        """Delete the project from tracker file and remove metadata."""
        # Read all projects except the one to delete
        projects = []
        with PROJECT_TRACKER_LOCK:
            with open(PROJECT_TRACKER_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    parts = list(
                        map(lambda x: x.strip(), line.strip().split(","))
                    )
                    if len(parts) >= 3:
                        project_dir = parts[2]
                        # Keep all projects except the one we're deleting
                        if project_dir != self.project_path:
                            projects.append(line)

            # Write back the filtered list
            with open(PROJECT_TRACKER_FILE, "w", encoding="utf-8") as f:
                f.writelines(projects)

        # Delete the atrament.json metadata file
        project_dir = Path(self.project_path)
        metadata_file = project_dir / "atrament.json"
        if metadata_file.exists():
            metadata_file.unlink()

        get_page_ref().update()

    async def rename_project(self, _):
        """Rename the project in tracker file and metadata."""
        page = get_page_ref()

        # Create a dialog for the new name
        new_name_field = ft.TextField(
            label="New Project Name",
            value=self.project_name.replace("...", ""),  # Remove truncation
            autofocus=True,
        )

        async def confirm_rename(_):
            new_name = new_name_field.value
            if not new_name:
                new_name_field.error = "Name cannot be empty"
                page.update()
                return

            # Sanitize name
            safe_name = new_name.replace(",", "")

            # Update PROJECT_TRACKER_FILE
            projects = []
            with PROJECT_TRACKER_LOCK:
                with open(PROJECT_TRACKER_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = list(
                            map(lambda x: x.strip(), line.strip().split(","))
                        )
                        if len(parts) >= 3:
                            _, last_edited, project_dir = (
                                parts[0],
                                parts[1],
                                parts[2],
                            )
                            if project_dir == self.project_path:
                                # Update this project's name
                                projects.append(
                                    f"{safe_name}, {last_edited}, {project_dir}\n"
                                )
                            else:
                                projects.append(line)
                        else:
                            projects.append(line)

                with open(PROJECT_TRACKER_FILE, "w", encoding="utf-8") as f:
                    f.writelines(projects)

            # Update atrament.json metadata file
            project_dir = Path(self.project_path)
            metadata_file = project_dir / "atrament.json"
            if metadata_file.exists():
                with open(metadata_file, "r", encoding="utf-8") as f:
                    project_data = json.load(f)
                project_data["metadata"]["name"] = new_name
                with open(metadata_file, "w", encoding="utf-8") as f:
                    json.dump(project_data, f, indent=4)

            # Update UI
            self.project_name = (
                safe_name if len(safe_name) <= 15 else safe_name[:15] + "..."
            )
            self.project_title.value = self.project_name

            # Close dialog
            dialog.open = False
            page.update()

        async def cancel_rename(_):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Rename Project"),
            content=new_name_field,
            actions=[
                ft.TextButton("Cancel", on_click=cancel_rename),
                ft.TextButton("Rename", on_click=confirm_rename),
            ],
        )

        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    async def copy_project_path(self, _):
        await ft.Clipboard().set(self.project_path)

    def init(self):
        if self.project_path == "NOT A VALID PATH":
            raise RuntimeError("Project path is not set")

        self.height = 50
        self.expand = True

        if len(self.project_name) > 15:
            self.project_name = self.project_name[:15] + "..."

        self.project_title = ft.Text(
            self.project_name,
            size=15,
            color=ft.Colors.WHITE,
            weight=ft.FontWeight.BOLD,
        )

        self.date_label = ft.Text(
            f"{self.last_time_edited}", size=10, color=ft.Colors.GREY_100
        )

        self.project_options = ft.PopupMenuButton(
            content=ft.Icon(ft.Icons.MORE_VERT, color=ft.Colors.WHITE),
            items=[
                ft.PopupMenuItem(
                    content="Delete", on_click=self.delete_project
                ),
                ft.PopupMenuItem(
                    content="Copy Path",
                    on_click=self.copy_project_path,
                ),
                ft.PopupMenuItem(
                    content="Rename", on_click=self.rename_project
                ),
            ],
            menu_position=ft.PopupMenuPosition.UNDER,
        )

        self.content = ft.Row(
            [
                self.project_title,
                ft.Row([self.date_label, self.project_options]),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        self.on_click = self.open_project


@ft.control
class PreviouseProjectList(ft.Column):
    @staticmethod
    def get_previouse_projects() -> list[ft.Control]:
        result = []

        with PROJECT_TRACKER_LOCK:
            with open(PROJECT_TRACKER_FILE, "a+") as file:
                file.seek(0)
                for line in file:
                    project_name, last_time_edited, project_dir = map(
                        lambda x: x.strip(), line.strip().split(",")
                    )

                    entry = ProjectEntry(
                        project_name=project_name,
                        last_time_edited=datetime.datetime.strptime(
                            last_time_edited, "%Y-%m-%d"
                        ).date(),
                        project_path=project_dir,
                    )
                    result.append(entry)

        return result

    def refresh_list(self):
        """Refresh the list by reloading projects from the tracker file."""
        self.controls.clear()
        self.controls = self.get_previouse_projects()

    def before_update(self):
        """Check if the project list has changed and refresh if needed."""
        self.controls.clear()
        self.controls = self.get_previouse_projects()

    def init(self):
        self.width = 300
        # TODO: MAKE THIS A ListView
        self.controls = self.get_previouse_projects()
