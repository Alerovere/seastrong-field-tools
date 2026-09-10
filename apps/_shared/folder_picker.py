"""
folder_picker.py

A click-through folder browser for Streamlit tools that need the user to
point at a folder on their own machine -- e.g. a large local dataset that
shouldn't be uploaded through the browser (see apps/README.md's "point at
large data, don't upload it" principle).

Docker containers can't browse the host filesystem on their own; they only
see what's explicitly mounted with `-v host_path:container_path`. Typing an
exact container-side path from memory is a common source of confusion (a
Mac path typed directly into the app, or a path that doesn't match what was
actually mounted, silently "not found" or empty). This widget mounts one
folder once, at a fixed container path, and lets the user navigate it
visually instead -- see each tool's README for the exact `-v` flag to use
alongside this.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

DEFAULT_ROOT = "/host"


def pick_folder(
    label: str,
    key: str,
    root: str = DEFAULT_ROOT,
    help: Optional[str] = None,
    allow_new: bool = False,
) -> Optional[str]:
    """
    Render a folder browser rooted at `root` (a path mounted into the
    container -- see module docstring) plus a "jump to a path" box for
    typing/pasting a path directly. Returns the currently browsed/selected
    absolute path (a string), or None if `root` isn't mounted at all (falls
    back to a plain text input in that case, so local `streamlit run`
    development without Docker still works).

    Parameters
    ----------
    label : str
        Shown above the widget.
    key : str
        Unique key -- use a different one per picker on the same page.
    root : str
        Container path the browser is confined to (can't navigate above
        it). Must match what you mounted with `-v host_path:root`.
    help : str, optional
        Extra explanatory text shown under the label.
    allow_new : bool
        If True, accepts a path that doesn't exist yet (e.g. for an output
        folder the caller will create) as long as it's still under `root`.
        If False (default -- appropriate for picking existing input data),
        a path that doesn't exist or isn't a directory is rejected and the
        browser resets to `root`.
    """
    root_path = Path(root)
    state_key = f"_picker_{key}_path"

    if not root_path.is_dir():
        st.caption(
            f"**{label}** -- `{root}` isn't mounted in this container, so "
            "folder browsing isn't available here. Enter a path directly "
            "(this only happens when running without Docker)."
        )
        return st.text_input(label, key=f"_picker_{key}_fallback", help=help) or None

    if state_key not in st.session_state:
        st.session_state[state_key] = str(root_path)

    current = Path(st.session_state[state_key])
    try:
        current.relative_to(root_path)
        if not allow_new and not current.is_dir():
            current = root_path
    except ValueError:
        current = root_path
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
        placeholder=f"...or paste a path under {root}",
    )
    if go_col.button("Go", key=f"_picker_{key}_go_{current}"):
        st.session_state[state_key] = manual
        st.rerun()

    return str(current)
