default:
    just --list

# Install all dependencies (extras + dependency groups)
install:
    uv sync --all-extras --all-groups

# Format code with ruff
format:
    uv run ruff format src/ tests/

# Format, then lint with ruff
lint: format
    uv run ruff check src/ tests/

# Run the test suite
test *ARGS:
    uv run pytest tests/ {{ ARGS }}

# Build the quartodoc API reference and render the Quarto documentation site
docs:
    rm -rf docs/api docs/objects.json public
    uv run quartodoc build --config docs/_quarto.yml
    quarto render docs

# Live-preview the documentation site
docs-preview:
    uv run quartodoc build --config docs/_quarto.yml
    quarto preview docs

# Lint + test, then bump the version (PATCH|MINOR|MAJOR), tag and push
bump level="PATCH": lint
    just test
    uv run cz bump --increment {{ level }}
    git push origin main --follow-tags
