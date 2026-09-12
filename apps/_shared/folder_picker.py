"""
folder_picker.py

A click-through folder browser for Streamlit tools that need the user to
point at a folder on their own machine -- e.g. a large local dataset that
shouldn't be uploaded through the browser (see apps/README.md's "point at
large data, don't upload it" principle).

These tools run directly on the user's machine (via a conda environment and
a double-click launcher -- see each tool's README), not inside a Docker
container, so there's no container filesystem boundary to work around: this
widget just lets the user click through their real folders instead of
typing a full path from memory, starting at their home directory by
default. There's also a "jump to path" box for pasting a path directly
(handy for a path copied from Finder, or an external drive under
`/Volumes/...`).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

# No real confinement needed now that this runs natively (not in a
# container) -- "/" means "anywhere this user account can read", same as
# Finder. `start` is where browsing begins, independent of `root`.
DEFAULT_ROOT = "/"


def pick_folder(
    label: str,
    key: str,
    root: str = DEFAULT_ROOT,
    start: Optional[str] = None,
    help: Optional[str] = None,
    allow_new: bool = False,
) -> Optional[str]:
    """
    Render a folder browser plus a "jump to a path" box for typing/pasting
    a path directly. Returns the currently browsed/selected absolute path
    (a string), or None if `root` doesn't exist on this machine at all
    (falls back to a plain text input in that vanishingly unlikely case).

    Parameters
    ----------
    label : str
        Shown above the widget.
    key : str
        Unique key -- use a different one per picker on the same page.
    root : str
        Path the browser is confined to (can't navigate above it).
        Defaults to "/" -- i.e. no real restriction, since this runs
        natively on the user's own machine.
    start : str, optional
        Where browsing begins. Defaults to the user's home directory.
    help : str, optional
        Extra explanatory text shown under the label.
    allow_new : bool
        If True, accepts a path that doesn't exist yet (e.g. for an output
        folder the caller will create) as long as it's still under `root`.
        If False (default -- appropriate for picking existing input data),
        a path that doesn't exist or isn't a directory is rejected and the
        browser resets to `start`.
    """
    root_path = Path(root)
    start_path = Path(start) if start else Path.home()
    state_key = f"_picker_{key}_path"

    if not root_path.is_dir():
        st.caption(
            f"**{label}** -- `{root}` isn't available on this machine, so "
            "folder browsing isn't available here. Enter a path directly."
        )
        return st.text_input(label, key=f"_picker_{key}_fallback", help=help) or None

    if state_key not in st.session_state:
        st.session_state[state_key] = str(start_path)

    current = Path(st.session_state[state_key])
    try:
        current.relative_to(root_path)
        if not allow_new and not current.is_dir():
            current = start_path
    except ValueError:
        current = start_path
    st.session_state[state_key] = str(current)

    st.markdown(f"**{label}**")
    if help:
        st.caption(help)

    col_up, col_path = st.columns([1, 6])
    if col_up.button(
        "⬆️ Up", key=f"_picker_{key}_up_{current}", disabled=(current == root_path)
    ):
        st.session_state[state_key] = str(current.parent)
        st.rerun()
    col_path.code(str(current))

    if current.is_dir():
        try:
            subdirs = sorted(
                p.name for p in current.iterdir() if p.is_dir() and not p.name.startswith(".")
            )
        except PermissionError:
            subdirs = []
            st.warning("Permission denied listing this folder.")
    else:
        subdirs = []
        if allow_new:
            st.caption("This folder doesn't exist yet -- it will be created.")

    if subdirs:
        choice = st.selectbox(
            "Open a subfolder",
            ["(browse into...)"] + subdirs,
            key=f"_picker_{key}_subdir_{current}",
        )
        if choice != "(browse into...)":
            st.session_state[state_key] = str(current / choice)
            st.rerun()
    elif current.is_dir():
        st.caption("No subfolders here.")

    jump_col, go_col = st.columns([5, 1])
    manual = jump_col.text_input(
        "jump_to_path",
        value=str(current),
        key=f"_picker_{key}_manual_{current}",
        label_visibility="collapsed",
        placeholder="...or paste a path (e.g. from Finder)",
    )
    if go_col.button("Go", key=f"_picker_{key}_go_{current}"):
        st.session_state[state_key] = manual
        st.rerun()

    return str(current)
