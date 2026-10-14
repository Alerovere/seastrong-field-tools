# Configuration file for the Sphinx documentation builder.

project = "SEASTRONG Field Processing Tools"
copyright = "2026, Ca' Foscari University of Venice (UNIVE)"
author = "Alessio Rovere and the SEASTRONG UNIVE team"
release = "1.0"

# General configuration
extensions = [
    "myst_parser",
    "sphinx_rtd_theme",
    "sphinxcontrib.rsvgconverter",  # SVG figures -> PDF for the PDF build
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# HTML output options
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_logo = "_static/Seastrong_logo_Trans.png"

html_theme_options = {
    "logo_only": False,
    "prev_next_buttons_location": "bottom",
    "collapse_navigation": False,
    "sticky_navigation": True,
    "navigation_depth": 3,
}

# MyST parser options (allows Markdown)
myst_enable_extensions = [
    "colon_fence",
    "deflist",
]
# Generate anchors for headings (for links like page.md#section)
myst_heading_anchors = 3

# PDF output (built by Read the Docs, see .readthedocs.yaml)
latex_engine = "xelatex"
latex_logo = "_static/Seastrong_logo_Trans.png"
latex_documents = [
    ("index", "seastrong-field-tools.tex", "SEASTRONG Field Processing Tools",
     "Alessio Rovere and the SEASTRONG UNIVE team", "manual"),
]
latex_elements = {
    "papersize": "a4paper",
    "pointsize": "10pt",
    "preamble": r"""
\usepackage{newunicodechar}
\newunicodechar{☐}{\(\square\)}
\newunicodechar{️}{}
""",
    "figure_align": "H",
}
