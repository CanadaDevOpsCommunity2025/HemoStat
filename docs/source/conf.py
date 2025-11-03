# Configuration file for Sphinx documentation builder.
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# Add the project root to the path so autodoc can import the packages
sys.path.insert(0, os.path.abspath('../..'))

# -- Project information -------------------------------------------------------
project = 'HemoStat'
copyright = '2025, The HemoStat Team'
author = 'The HemoStat Team'
version = '0.1.0'
release = '0.1.0'

# -- General configuration -----------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',              # Auto-generates API docs from Python docstrings
    'sphinx.ext.autosummary',          # Generate summary tables of modules/classes
    'sphinx.ext.napoleon',             # Parses Google-style docstrings
    'sphinx.ext.viewcode',             # Add links to highlighted source code
    'sphinx.ext.intersphinx',          # Link to external docs
    'sphinx.ext.githubpages',          # Create .nojekyll file for GitHub Pages
    'myst_parser',                     # Parse Markdown files
    'sphinx_copybutton',               # Add copy buttons to code blocks
    'sphinxcontrib.mermaid',           # Render mermaid diagrams
]

# -- Napoleon settings (for Google-style docstrings) --------------------------
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = True

# -- Autodoc settings (controls how docstrings are extracted) -----------------
autodoc_typehints = 'description'
autodoc_typehints_description_target = 'documented_params'
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
    'special-members': '__init__',
}

# Mock heavy dependencies to avoid import errors during doc build
autodoc_mock_imports = [
    'docker',
    'redis',
    'streamlit',
    'pandas',
    'langchain',
    'langchain_openai',
    'langchain_anthropic',
    'langchain_huggingface',
    'openai',
    'anthropic',
]

# -- Autosummary settings -------------------------------------------------------
autosummary_generate = True

# -- MyST settings (for Markdown integration) ---------------------------------
myst_enable_extensions = ['colon_fence', 'deflist', 'html_image']
source_suffix = {'.rst': 'restructuredtext', '.md': 'markdown'}

# -- Theme and HTML settings --------------------------------------------------
html_theme = 'sphinx_rtd_theme'
html_title = 'HemoStat Documentation'
html_static_path = []

html_theme_options = {
    'navigation_depth': 3,
}

# -- Intersphinx mapping (for cross-references) -------------------------------
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'docker': ('https://docker-py.readthedocs.io/en/stable/', None),
}

# -- Build output configuration -----------------------------------------------
# Build directly into docs/ (parent directory) for GitHub Pages
# The build output will be in /docs which GitHub Pages is configured to serve
