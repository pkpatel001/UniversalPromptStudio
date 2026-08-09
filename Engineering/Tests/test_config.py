"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Configuration System Tests

Tests cover:
- successful loading of all configuration sections
- immutability of frozen dataclasses
- singleton/cache behavior
- missing configuration directory
- missing configuration file
- invalid root key
- missing required key
- invalid value types
- invalid nested structures
- unknown key rejection
- filename/root-key mismatch

===============================================================================
"""

from __future__ import annotations

import textwrap
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from Engineering.core.config import (
    Configuration,
    DocumentationConfiguration,
    DocumentationGenerateConfiguration,
    EngineeringConfiguration,
    LoggingConfiguration,
    ProjectConfiguration,
    get_config,
)
from Engineering.core.exceptions import ConfigurationFileNotFoundError, ConfigurationValidationError

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _write_yaml(path: Path, content: str) -> None:
    path.write_text(textwrap.dedent(content), encoding="utf-8")


def _create_valid_project_yaml(path: Path) -> None:
    _write_yaml(
        path,
        """\
        project:
          name: "Universal Prompt Studio"
          short_name: "UPS"
          company: "The Patel Brothers Creative Solutions"
          version: "0.2.0-alpha"
          license: "Mozilla Public License 2.0"
          python:
            minimum_version: "3.12"
        """,
    )


def _create_valid_engineering_yaml(path: Path) -> None:
    _write_yaml(
        path,
        """\
        engineering:
          strict_mode: true
          diagnostics: true
          cache:
            enabled: true
          validation:
            enabled: true
          paths:
            verify_on_startup: true
        """,
    )


def _create_valid_documentation_yaml(path: Path) -> None:
    _write_yaml(
        path,
        """\
        documentation:
          enabled: true
          output:
            root: "Engineering/Documentation/Generated"
          generate:
            readme: true
            api: true
            architecture: true
            adrs: true
            project_status: true
            changelog: true
            index: true
            manifests: true
        """,
    )


def _create_valid_logging_yaml(path: Path) -> None:
    _write_yaml(
        path,
        """\
        logging:
          enabled: true
          level: "INFO"
          console: true
          file: true
          directory: "Engineering/Documentation/Logs"
          filename: "engineering.log"
        """,
    )


# -----------------------------------------------------------------------------
# Successful Loading
# -----------------------------------------------------------------------------


class TestGetConfigSuccess:
    """Tests for successful configuration loading."""

    def test_get_config_loads_all_sections(self) -> None:
        config = get_config()

        assert isinstance(config, Configuration)

        assert isinstance(config.project, ProjectConfiguration)
        assert isinstance(config.engineering, EngineeringConfiguration)
        assert isinstance(config.documentation, DocumentationConfiguration)
        assert isinstance(config.logging, LoggingConfiguration)

    def test_get_config_project_values(self) -> None:
        config = get_config()

        assert config.project.name == "Universal Prompt Studio"
        assert config.project.short_name == "UPS"
        assert config.project.company == "The Patel Brothers Creative Solutions"
        assert config.project.version == "0.2.0-alpha"
        assert config.project.license == "Mozilla Public License 2.0"
        assert config.project.python.minimum_version == "3.12"

    def test_get_config_engineering_values(self) -> None:
        config = get_config()

        assert config.engineering.strict_mode is True
        assert config.engineering.diagnostics is True
        assert config.engineering.cache.enabled is True
        assert config.engineering.validation.enabled is True
        assert config.engineering.paths.verify_on_startup is True

    def test_get_config_documentation_values(self) -> None:
        config = get_config()

        assert config.documentation.enabled is True
        assert config.documentation.output.root == "Engineering/Documentation/Generated"

        generate = config.documentation.generate
        assert isinstance(generate, DocumentationGenerateConfiguration)
        assert generate.readme is True
        assert generate.api is True
        assert generate.architecture is True
        assert generate.adrs is True
        assert generate.project_status is True
        assert generate.changelog is True
        assert generate.index is True
        assert generate.manifests is True

    def test_get_config_logging_values(self) -> None:
        config = get_config()

        assert config.logging.enabled is True
        assert config.logging.level == "INFO"
        assert config.logging.console is True
        assert config.logging.file is True
        assert config.logging.directory == "Engineering/Documentation/Logs"
        assert config.logging.filename == "engineering.log"


# -----------------------------------------------------------------------------
# Immutability
# -----------------------------------------------------------------------------


class TestConfigImmutability:
    """Tests for frozen dataclass immutability."""

    def test_project_name_is_immutable(self) -> None:
        config = get_config()

        with pytest.raises(FrozenInstanceError):
            config.project.name = "Changed"

    def test_python_minimum_version_is_immutable(self) -> None:
        config = get_config()

        with pytest.raises(FrozenInstanceError):
            config.project.python.minimum_version = "3.13"

    def test_engineering_strict_mode_is_immutable(self) -> None:
        config = get_config()

        with pytest.raises(FrozenInstanceError):
            config.engineering.strict_mode = False

    def test_logging_level_is_immutable(self) -> None:
        config = get_config()

        with pytest.raises(FrozenInstanceError):
            config.logging.level = "DEBUG"

    def test_documentation_output_root_is_immutable(self) -> None:
        config = get_config()

        with pytest.raises(FrozenInstanceError):
            config.documentation.output.root = "changed"


# -----------------------------------------------------------------------------
# Cache Behavior
# -----------------------------------------------------------------------------


class TestConfigCache:
    """Tests for singleton/cache behavior."""

    def test_get_config_returns_same_instance(self) -> None:
        config1 = get_config()
        config2 = get_config()

        assert config1 is config2

    def test_get_config_cache_clear(self) -> None:
        config1 = get_config()
        get_config.cache_clear()
        config2 = get_config()

        assert config1 is not config2
        assert config1 == config2


# -----------------------------------------------------------------------------
# Missing Configuration Directory
# -----------------------------------------------------------------------------


class TestMissingConfigDirectory:
    """Tests for missing configuration directory."""

    def test_missing_config_directory_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from Engineering.core import config as config_module

        original_get_paths = config_module.get_paths
        config_module.get_config.cache_clear()

        class FakePaths:
            config = Path("nonexistent_directory_xyz")

        monkeypatch.setattr(config_module, "get_paths", lambda: FakePaths())

        with pytest.raises(
            ConfigurationFileNotFoundError,
            match="Configuration directory not found",
        ):
            get_config()

        monkeypatch.setattr(config_module, "get_paths", original_get_paths)
        config_module.get_config.cache_clear()


# -----------------------------------------------------------------------------
# Missing Configuration File
# -----------------------------------------------------------------------------


class TestMissingConfigFile:
    """Tests for missing configuration files."""

    def test_missing_project_yaml(self, tmp_path: Path) -> None:
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        _create_valid_engineering_yaml(config_dir / "engineering.yaml")
        _create_valid_documentation_yaml(config_dir / "documentation.yaml")
        _create_valid_logging_yaml(config_dir / "logging.yaml")

        from Engineering.core.config import _load_project_config

        with pytest.raises(ConfigurationFileNotFoundError):
            _load_project_config(config_dir / "project.yaml")

    def test_missing_logging_yaml(self, tmp_path: Path) -> None:
        from Engineering.core.config import _load_logging_config

        with pytest.raises(ConfigurationFileNotFoundError):
            _load_logging_config(tmp_path / "logging.yaml")


# -----------------------------------------------------------------------------
# Invalid Root Key
# -----------------------------------------------------------------------------


class TestInvalidRootKey:
    """Tests for invalid root key validation."""

    def test_root_key_mismatch(self, tmp_path: Path) -> None:
        config_file = tmp_path / "wrong_name.yaml"
        _write_yaml(
            config_file,
            """\
            engineering:
              strict_mode: true
            """,
        )

        from Engineering.core.config import _load_config

        with pytest.raises(
            ConfigurationValidationError,
            match="filename stem.*does not match expected root key",
        ):
            _load_config(config_file, "engineering", ("strict_mode",))

    def test_missing_root_key(self, tmp_path: Path) -> None:
        config_file = tmp_path / "project.yaml"
        _write_yaml(
            config_file,
            """\
            other:
              name: "Test"
            """,
        )

        from Engineering.core.config import _load_config

        with pytest.raises(
            ConfigurationValidationError,
            match="expected root key 'project' not found",
        ):
            _load_config(config_file, "project", ("name",))

    def test_root_key_not_mapping(self, tmp_path: Path) -> None:
        config_file = tmp_path / "project.yaml"
        _write_yaml(
            config_file,
            """\
            project: "not a mapping"
            """,
        )

        from Engineering.core.config import _load_config

        with pytest.raises(
            ConfigurationValidationError,
            match="expected root key 'project' to be a mapping",
        ):
            _load_config(config_file, "project", ("name",))


# -----------------------------------------------------------------------------
# Missing Required Keys
# -----------------------------------------------------------------------------


class TestMissingRequiredKeys:
    """Tests for missing required key validation."""

    def test_missing_project_name(self, tmp_path: Path) -> None:
        config_file = tmp_path / "project.yaml"
        _write_yaml(
            config_file,
            """\
            project:
              short_name: "UPS"
              company: "Test"
              version: "0.1.0"
              license: "MIT"
              python:
                minimum_version: "3.12"
            """,
        )

        from Engineering.core.config import _load_project_config

        with pytest.raises(
            ConfigurationValidationError,
            match="Missing required configuration key",
        ):
            _load_project_config(config_file)

    def test_missing_nested_key(self, tmp_path: Path) -> None:
        config_file = tmp_path / "engineering.yaml"
        _write_yaml(
            config_file,
            """\
            engineering:
              strict_mode: true
              diagnostics: true
              cache:
                enabled: true
              validation:
                enabled: true
              paths: {}
            """,
        )

        from Engineering.core.config import _load_engineering_config

        with pytest.raises(
            ConfigurationValidationError,
            match="Missing required configuration key",
        ):
            _load_engineering_config(config_file)


# -----------------------------------------------------------------------------
# Unknown Keys
# -----------------------------------------------------------------------------


class TestUnknownKeys:
    """Tests for unknown key rejection."""

    def test_unknown_root_key(self, tmp_path: Path) -> None:
        config_file = tmp_path / "project.yaml"
        _write_yaml(
            config_file,
            """\
            project:
              name: "Test"
              short_name: "UPS"
              company: "Test"
              version: "0.1.0"
              license: "MIT"
              python:
                minimum_version: "3.12"
              unknown_field: true
            """,
        )

        from Engineering.core.config import _load_project_config

        with pytest.raises(ConfigurationValidationError, match="Unknown configuration key"):
            _load_project_config(config_file)

    def test_unknown_nested_key(self, tmp_path: Path) -> None:
        config_file = tmp_path / "engineering.yaml"
        _write_yaml(
            config_file,
            """\
            engineering:
              strict_mode: true
              diagnostics: true
              cache:
                enabled: true
                unknown_nested: true
              validation:
                enabled: true
              paths:
                verify_on_startup: true
            """,
        )

        from Engineering.core.config import _load_engineering_config

        with pytest.raises(ConfigurationValidationError, match="Unknown configuration key"):
            _load_engineering_config(config_file)

    def test_unknown_logging_key(self, tmp_path: Path) -> None:
        config_file = tmp_path / "logging.yaml"
        _write_yaml(
            config_file,
            """\
            logging:
              enabled: true
              level: "INFO"
              console: true
              file: true
              directory: "Logs"
              filename: "app.log"
              extra_key: "value"
            """,
        )

        from Engineering.core.config import _load_logging_config

        with pytest.raises(ConfigurationValidationError, match="Unknown configuration key"):
            _load_logging_config(config_file)


# -----------------------------------------------------------------------------
# Invalid Value Types
# -----------------------------------------------------------------------------


class TestInvalidValueTypes:
    """Tests for strict type validation."""

    def test_string_instead_of_bool(self, tmp_path: Path) -> None:
        config_file = tmp_path / "engineering.yaml"
        _write_yaml(
            config_file,
            """\
            engineering:
              strict_mode: "true"
              diagnostics: true
              cache:
                enabled: true
              validation:
                enabled: true
              paths:
                verify_on_startup: true
            """,
        )

        from Engineering.core.config import _load_engineering_config

        with pytest.raises(ConfigurationValidationError, match="expected bool, received str"):
            _load_engineering_config(config_file)

    def test_int_instead_of_bool(self, tmp_path: Path) -> None:
        config_file = tmp_path / "logging.yaml"
        _write_yaml(
            config_file,
            """\
            logging:
              enabled: 1
              level: "INFO"
              console: true
              file: true
              directory: "Logs"
              filename: "app.log"
            """,
        )

        from Engineering.core.config import _load_logging_config

        with pytest.raises(ConfigurationValidationError, match="expected bool, received int"):
            _load_logging_config(config_file)

    def test_int_instead_of_str(self, tmp_path: Path) -> None:
        config_file = tmp_path / "project.yaml"
        _write_yaml(
            config_file,
            """\
            project:
              name: 12345
              short_name: "UPS"
              company: "Test"
              version: "0.1.0"
              license: "MIT"
              python:
                minimum_version: "3.12"
            """,
        )

        from Engineering.core.config import _load_project_config

        with pytest.raises(ConfigurationValidationError, match="expected str, received int"):
            _load_project_config(config_file)

    def test_list_instead_of_mapping(self, tmp_path: Path) -> None:
        config_file = tmp_path / "engineering.yaml"
        _write_yaml(
            config_file,
            """\
            engineering:
              strict_mode: true
              diagnostics: true
              cache: []
              validation:
                enabled: true
              paths:
                verify_on_startup: true
            """,
        )

        from Engineering.core.config import _load_engineering_config

        with pytest.raises(ConfigurationValidationError, match="expected mapping, received list"):
            _load_engineering_config(config_file)


# -----------------------------------------------------------------------------
# Invalid Nested Structures
# -----------------------------------------------------------------------------


class TestInvalidNestedStructures:
    """Tests for invalid nested configuration structures."""

    def test_generate_not_mapping(self, tmp_path: Path) -> None:
        config_file = tmp_path / "documentation.yaml"
        _write_yaml(
            config_file,
            """\
            documentation:
              enabled: true
              output:
                root: "Generated"
              generate: true
            """,
        )

        from Engineering.core.config import _load_documentation_config

        with pytest.raises(ConfigurationValidationError, match="expected mapping, received bool"):
            _load_documentation_config(config_file)

    def test_output_not_mapping(self, tmp_path: Path) -> None:
        config_file = tmp_path / "documentation.yaml"
        _write_yaml(
            config_file,
            """\
            documentation:
              enabled: true
              output: "Generated"
              generate:
                readme: true
                api: true
                architecture: true
                adrs: true
                project_status: true
                changelog: true
                index: true
                manifests: true
            """,
        )

        from Engineering.core.config import _load_documentation_config

        with pytest.raises(ConfigurationValidationError, match="expected mapping, received str"):
            _load_documentation_config(config_file)

    def test_python_not_mapping(self, tmp_path: Path) -> None:
        config_file = tmp_path / "project.yaml"
        _write_yaml(
            config_file,
            """\
            project:
              name: "Test"
              short_name: "UPS"
              company: "Test"
              version: "0.1.0"
              license: "MIT"
              python: "3.12"
            """,
        )

        from Engineering.core.config import _load_project_config

        with pytest.raises(ConfigurationValidationError, match="expected mapping, received str"):
            _load_project_config(config_file)
