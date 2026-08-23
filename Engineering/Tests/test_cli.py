"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

CLI Tests

Tests cover:
- Application startup
- Version command
- Help rendering
- Validation command (success/failure/output)
- Configuration command
- Error handling
- Command isolation

===============================================================================
"""

from __future__ import annotations

from typer.testing import CliRunner

from Engineering.cli.app import app

runner = CliRunner()


class TestCLIApp:
    """Tests for the CLI application."""

    def test_app_startup(self) -> None:
        """Test that the application starts without command."""
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "Universal Prompt Studio" in result.output
        assert "Engineering Toolkit" in result.output
        assert "Quick Start" in result.output

    def test_help(self) -> None:
        """Test that help renders successfully."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "validate" in result.output
        assert "config" in result.output
        assert "version" in result.output
        assert "doctor" in result.output
        assert "docs" in result.output
        assert "build" in result.output
        assert "generate" in result.output
        assert "release" in result.output
        assert "plugin" in result.output


class TestVersionCommand:
    """Tests for the version command."""

    def test_version(self) -> None:
        """Test version command output."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "Engineering Toolkit" in result.output
        assert "0.2.0-alpha" in result.output


class TestValidateCommand:
    """Tests for the validate command."""

    def test_validate_runs(self) -> None:
        """Test that validate command runs (may pass or fail)."""
        result = runner.invoke(app, ["validate"])
        # The project may have validation errors, so we accept either
        assert result.exit_code in (0, 1)
        assert "Engineering Validation" in result.output

    def test_validate_output_format(self) -> None:
        """Test that validation output contains expected sections."""
        result = runner.invoke(app, ["validate"])
        assert "Engineering Validation" in result.output
        assert "error(s)" in result.output
        assert "warning(s)" in result.output


class TestConfigCommand:
    """Tests for the config command."""

    def test_config_show(self) -> None:
        """Test config command output."""
        result = runner.invoke(app, ["config"])
        assert result.exit_code == 0
        assert "Project" in result.output
        assert "Universal Prompt Studio" in result.output
        assert "Engineering" in result.output
        assert "Strict Mode" in result.output
        assert "Documentation" in result.output
        assert "Enabled" in result.output


class TestFutureCommands:
    """Tests for future command groups."""

    def test_doctor_help(self) -> None:
        """Test doctor command help."""
        result = runner.invoke(app, ["doctor", "--help"])
        assert result.exit_code == 0
        assert "check" in result.output
        assert "info" in result.output

    def test_docs_help(self) -> None:
        """Test docs command help."""
        result = runner.invoke(app, ["docs", "--help"])
        assert result.exit_code == 0
        assert "generate" in result.output
        assert "validate" in result.output

    def test_build_help(self) -> None:
        """Test build command help."""
        result = runner.invoke(app, ["build", "--help"])
        assert result.exit_code == 0
        assert "clean" in result.output
        assert "run" in result.output

    def test_generate_help(self) -> None:
        """Test generate command help."""
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        assert "provider" in result.output
        assert "plugin" in result.output

    def test_release_help(self) -> None:
        """Test release command help."""
        result = runner.invoke(app, ["release", "--help"])
        assert result.exit_code == 0
        assert "plan" in result.output
        assert "run" in result.output
        assert "clean" in result.output

    def test_doctor_no_subcommand(self) -> None:
        """Test doctor without subcommand shows usage guidance."""
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "doctor check" in result.output.lower()
        assert "doctor info" in result.output.lower()

    def test_docs_no_subcommand(self) -> None:
        """Test docs without subcommand shows usage guidance."""
        result = runner.invoke(app, ["docs"])
        assert result.exit_code == 0
        assert "docs generate" in result.output.lower()
        assert "docs validate" in result.output.lower()

    def test_build_no_subcommand(self) -> None:
        """Test build without subcommand."""
        result = runner.invoke(app, ["build"])
        assert result.exit_code == 0
        assert "build run" in result.output.lower()

    def test_generate_no_subcommand(self) -> None:
        """Test generate without subcommand."""
        result = runner.invoke(app, ["generate"])
        assert result.exit_code == 0
        assert "not yet implemented" in result.output.lower()

    def test_release_no_subcommand(self) -> None:
        """Test release without subcommand."""
        result = runner.invoke(app, ["release"])
        assert result.exit_code == 0
        assert "release plan" in result.output.lower()


class TestErrorHandling:
    """Tests for CLI error handling."""

    def test_invalid_command(self) -> None:
        """Test that invalid commands show error."""
        result = runner.invoke(app, ["nonexistent"])
        assert result.exit_code != 0


class TestCommandIsolation:
    """Tests for command isolation - commands don't execute unrelated subsystems."""

    def test_version_does_not_validate(self) -> None:
        """Version command should not run validation."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "Engineering Validation" not in result.output

    def test_config_does_not_validate(self) -> None:
        """Config command should not run validation."""
        result = runner.invoke(app, ["config"])
        assert result.exit_code == 0
        assert "Engineering Validation" not in result.output
