# HemoStat Documentation

This directory contains both the source files and generated documentation for HemoStat.

## Directory Structure

- **`source/`** - Sphinx source files (`.rst` and `.md`)
  - `conf.py` - Sphinx configuration
  - `index.rst` - Documentation index
  - `*.md` - User guides (quickstart, architecture, deployment, etc.)
  - `api/` - API reference (auto-generated from Python docstrings)

- **Generated HTML** - Built documentation served by GitHub Pages
  - `*.html` - Generated HTML files
  - `_static/` - Static assets (CSS, JavaScript, images)
  - `_sources/` - Source file copies
  - `_modules/` - Module documentation
  - `objects.inv` - Sphinx inventory for cross-references

## Building Documentation

### Install Dependencies

```bash
make docs-install
# or
uv sync --extra docs
```

### Build Documentation

```bash
make docs-build
# or
sphinx-build -b html docs/source docs
```

This generates HTML files directly into the `/docs` directory, which GitHub Pages is configured to serve.

### Serve Locally

```bash
make docs-serve
# or
sphinx-build -b html docs/source docs && python -m http.server -d docs 8000
```

View at http://localhost:8000

### Clean Build Artifacts

```bash
make docs-clean
```

## About the Build Process

1. **Source files** in `docs/source/` are written in reStructuredText (`.rst`) and Markdown (`.md`)
2. **Sphinx** processes these files and generates HTML
3. **Autodoc extension** automatically extracts API documentation from Python docstrings
4. **Napoleon extension** parses Google-style docstrings
5. **MyST parser** enables Markdown support
6. **Generated HTML** is output directly to `/docs` for GitHub Pages

## API Documentation

The API Reference is **auto-generated from Python docstrings** using Sphinx autodoc:

- All classes, methods, and functions are documented
- Google-style docstrings are automatically converted to HTML
- Type hints are included in the documentation
- Source code links are provided for each item

See `docs/source/api/` for the autodoc directives that generate this documentation.

## GitHub Pages Configuration

GitHub Pages is configured to serve from the `/docs` directory on the main branch:

1. Generated HTML files are committed to the repository
2. GitHub Pages automatically serves them at https://jondmarien.github.io/HemoStat/
3. The `.nojekyll` file tells GitHub Pages to skip Jekyll processing (required for Sphinx)

## Live Documentation

The built documentation is available at: https://quartz.chron0.tech/HemoStat/

## Development Workflow

1. Edit source files in `docs/source/`
2. Write/update Python docstrings in the code
3. Run `make docs-build` to generate HTML
4. Review changes locally with `make docs-serve`
5. Commit both source files and generated HTML
6. GitHub Pages automatically updates the live site

## Sphinx Extensions Used

- **autodoc** - Auto-generates API docs from Python docstrings
- **autosummary** - Generates summary tables of modules/classes
- **napoleon** - Parses Google-style docstrings
- **viewcode** - Links to highlighted source code
- **intersphinx** - Cross-references to external docs
- **githubpages** - Creates `.nojekyll` file
- **myst_parser** - Markdown support
- **sphinx_copybutton** - Copy buttons for code blocks
- **sphinxcontrib.mermaid** - Mermaid diagram support

## Theme

Uses the official **ReadTheDocs theme** (`sphinx-rtd-theme`) for professional documentation styling.

## Troubleshooting

### Build Fails

```bash
# Clean and rebuild
make docs-clean
make docs-build
```

### Missing Dependencies

```bash
# Reinstall docs dependencies
make docs-install
```

### Changes Not Appearing

1. Ensure you edited the correct source file in `docs/source/`
2. Run `make docs-build` to regenerate HTML
3. Clear your browser cache or use Ctrl+Shift+R to force refresh

### Autodoc Not Finding Modules

The `conf.py` mocks heavy dependencies to avoid import errors:
- `docker`, `redis`, `streamlit`, `langchain`, `openai`, `anthropic`

If autodoc still fails, check that the module is importable from the project root.
