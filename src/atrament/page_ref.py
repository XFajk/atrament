import flet as ft

_main_page_ref: ft.Page | None = None


def set_page_ref(page: ft.Page):
    """Set the global page reference."""
    global _main_page_ref
    _main_page_ref = page


def get_page_ref() -> ft.Page:
    """Get the global page reference."""
    if _main_page_ref is None:
        raise RuntimeError("Page not initialized. Call set_page() first.")
    return _main_page_ref
