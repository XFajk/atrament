import json
from typing import Any

import flet as ft
import keyring

from atrament.const import (
    DEFAULT_SETTINGS,
    USER_SETTINGS_FILE,
    USER_SETTINGS_LOCK,
)
from atrament.page_ref import get_page_ref
from atrament.sections.section import Section


def is_secret(key: str) -> bool:
    return "key" in key.lower() or "password" in key.lower()


class SettingsSection(Section):
    _route = "/settings/"

    def __init__(self):
        self.inputs: dict[str, dict[str, Any]] = {}
        self.save_button: ft.Button | None = None

    @staticmethod
    def route() -> str:
        return SettingsSection._route

    def save_settings(self, e):
        """Save current input values to settings file."""
        new_settings = {}

        # Reconstruct settings dictionary from inputs
        for section, fields in self.inputs.items():
            new_settings[section] = {}
            for key, control in fields.items():
                value = control.value
                # Convert empty strings back to None if that matches the default type
                if not value:
                    value = None

                # special handling of secret data
                if is_secret(key):
                    keyring.set_password(
                        "atrament", f"{section}:{key}", value or ""
                    )
                    new_settings[section][key] = None
                else:
                    new_settings[section][key] = value

        # Ensure directory exists
        USER_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Write to file
        with USER_SETTINGS_LOCK:
            with open(USER_SETTINGS_FILE, "w") as f:
                json.dump(new_settings, f, indent=4)

        # Show feedback
        e.control.content = "Saved!"
        e.control.bgcolor = ft.Colors.GREEN
        e.control.update()

    def reset_save_button(self, _):
        if self.save_button is None:
            return

        self.save_button.content = "Save Settings"
        self.save_button.bgcolor = ft.Colors.BLUE
        self.save_button.update()

    async def go_back(self, _):
        page = get_page_ref()
        if len(page.views) > 1:
            page.views.pop()
            top_view = page.views[-1]
            await page.push_route(top_view.route or "/")
        else:
            page.views.pop()
            await page.push_route("/")

    def render(self):
        # Load user settings from file
        user_settings = {}
        if USER_SETTINGS_FILE.exists():
            with USER_SETTINGS_LOCK:
                try:
                    with open(USER_SETTINGS_FILE, "r") as f:
                        user_settings = json.load(f)
                except Exception:
                    pass  # Ignore errors, will fall back to defaults

        self.inputs = {}  # Reset inputs map
        controls_list = []

        # Header
        controls_list.append(
            ft.Row(
                [
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK, on_click=self.go_back
                    ),
                    ft.Text(
                        "Application Settings",
                        size=30,
                        weight=ft.FontWeight.BOLD,
                    ),
                ]
            )
        )
        controls_list.append(ft.Divider())

        # Iterate through DEFAULT_SETTINGS to build UI structure
        # This ensures we always show all available settings, even if not in user file yet
        for section_name, default_section_values in DEFAULT_SETTINGS.items():
            # Section Title
            controls_list.append(
                ft.Text(
                    section_name,
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE,
                )
            )

            self.inputs[section_name] = {}

            # Get user values for this section if they exist
            user_section_values = user_settings.get(section_name, {})

            if isinstance(default_section_values, dict):
                for key, default_val in default_section_values.items():
                    # Determine value: user value > default value
                    # handle secret values
                    if is_secret(key):
                        current_val = keyring.get_password(
                            "atrament", f"{section_name}:{key}"
                        )
                    else:
                        current_val = user_section_values.get(key, default_val)

                    # Determine if it looks like a password/key for masking
                    is_password = is_secret(key)  # cache the value

                    tf = ft.TextField(
                        label=key,
                        value=current_val if current_val is not None else "",
                        password=is_password,
                        can_reveal_password=is_password,
                        border_color=ft.Colors.BLUE_200,
                        on_click=self.reset_save_button,
                    )
                    self.inputs[section_name][key] = tf
                    controls_list.append(tf)

            controls_list.append(
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT)
            )

        # Save Button
        self.save_button = ft.Button(
            "Save Settings",
            icon=ft.Icons.SAVE,
            bgcolor=ft.Colors.BLUE,
            color=ft.Colors.WHITE,
            on_click=self.save_settings,
            height=50,
        )

        controls_list.append(ft.Divider())
        controls_list.append(self.save_button)
        # Add some bottom padding
        controls_list.append(ft.Container(height=50))

        return ft.View(
            route=self.route(),
            controls=[
                ft.Container(
                    content=ft.Column(
                        controls=controls_list,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    padding=20,
                    expand=True,
                )
            ],
        )
