"""
Shared branding/theme helpers for SEASTRONG Streamlit tools.

Every tool under apps/<tool_name>/ imports this module (it's copied into the
Docker image alongside the tool -- see each tool's Dockerfile) so that all
tools present the same header, color palette, and page chrome without each
one re-implementing it.

To add a new tool with the same look:
    from _shared.branding import apply_page_config, render_header
    apply_page_config("My Tool")
    render_header("My Tool", "One-line description of what it does")
"""
from __future__ import annotations

import streamlit as st

# Palette. NOTE: placeholder ocean-blue tones, not sampled from the official
# SEASTRONG logo -- swap these for the exact brand colors when available.
PRIMARY_COLOR = "#0f6e8c"
ACCENT_COLOR = "#4CAF50"
MUTED_TEXT_COLOR = "#5a6b70"


def apply_page_config(title: str, icon: str = "\U0001F30A") -> None:
    """Call once, first, at the top of a tool's app.py."""
    st.set_page_config(
        page_title=f"{title} - SEASTRONG",
        page_icon=icon,
        layout="wide",
    )


def render_header(title: str, subtitle: str = "") -> None:
    """Render the shared SEASTRONG header block used by every tool."""
    subtitle_html = (
        f'<p style="margin:0;color:{MUTED_TEXT_COLOR};font-size:0.95rem;">{subtitle}</p>'
        if subtitle
        else ""
    )
    st.markdown(
        f"""
        <div style="padding-bottom:0.6rem;border-bottom:3px solid {PRIMARY_COLOR};
                    margin-bottom:1.5rem;">
            <p style="margin:0;color:{PRIMARY_COLOR};font-weight:600;
                      letter-spacing:0.08em;font-size:0.8rem;text-transform:uppercase;">
                SEASTRONG Field Tools
            </p>
            <h1 style="margin:0.1rem 0 0 0;color:#111;">{title}</h1>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer(source_note: str = "") -> None:
    """Optional shared footer -- link back to readthedocs, repo, etc."""
    st.markdown(
        f"""
        <hr style="margin-top:2.5rem;">
        <p style="color:{MUTED_TEXT_COLOR};font-size:0.8rem;">
            Part of the
            <a href="https://seastrong-field-tools.readthedocs.io" target="_blank">
                SEASTRONG Field Processing Tools
            </a> repository. {source_note}
        </p>
        """,
        unsafe_allow_html=True,
    )
