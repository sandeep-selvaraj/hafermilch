import nox

# Use uv for all virtual environment management
nox.options.default_venv_backend = "uv"

# Run both sessions by default
nox.options.sessions = ["lint", "tests"]


@nox.session
def lint(session: nox.Session) -> None:
    """Run pre-commit hooks (ruff lint + format) across all files."""
    session.install("pre-commit")
    session.run("pre-commit", "run", "--all-files")


@nox.session
def tests(session: nox.Session) -> None:
    """Run the test suite with pytest.

    Pass extra pytest arguments after a double-dash, e.g.:
        uv run nox -s tests -- -k test_llm -v
    """
    session.install("pytest", "pytest-asyncio")
    session.install("-e", ".")
    session.run("pytest", "tests/", *session.posargs)
