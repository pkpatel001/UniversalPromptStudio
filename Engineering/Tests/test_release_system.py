"""E-011 release-system domain, inspection, and manifest tests."""

from __future__ import annotations

import hashlib
import io
import json
import struct
import subprocess
import tarfile
import zipfile
from pathlib import Path

import pytest

from Engineering.core.exceptions import ReleaseError
from Engineering.ReleaseSystem import (
    DesktopPackageBuilder,
    FrontendPackageBuilder,
    PackageArtifact,
    PackageFormat,
    PackageInspector,
    PackageState,
    ReleaseContext,
    ReleaseManifest,
    ReleasePlanner,
    ReleasePreconditionChecker,
    ReleasePreconditionReport,
    ReleaseService,
    ReleaseVersion,
)


def _context(tmp_path: Path, *, dry_run: bool = False) -> ReleaseContext:
    return ReleaseContext(
        tmp_path,
        tmp_path / "release",
        ReleaseVersion("0.2.0-alpha"),
        dry_run=dry_run,
    )


class TestReleaseVersionAndPlanning:
    def test_normalizes_python_version(self) -> None:
        version = ReleaseVersion("0.2.0-alpha")

        assert version.normalized == "0.2.0a0"

    def test_rejects_invalid_version(self) -> None:
        with pytest.raises(ReleaseError, match="Invalid release version"):
            ReleaseVersion("not a version")

    def test_plan_is_deterministic(self, tmp_path: Path) -> None:
        plan = ReleasePlanner().plan(
            _context(tmp_path),
            (
                PackageFormat.FRONTEND_ZIP,
                PackageFormat.WHEEL,
                PackageFormat.SDIST,
            ),
        )

        assert tuple(spec.package_format for spec in plan.specs) == (
            PackageFormat.SDIST,
            PackageFormat.WHEEL,
            PackageFormat.FRONTEND_ZIP,
        )

    def test_rejects_empty_and_duplicate_formats(self, tmp_path: Path) -> None:
        planner = ReleasePlanner()
        with pytest.raises(ReleaseError, match="At least one"):
            planner.plan(_context(tmp_path), ())
        with pytest.raises(ReleaseError, match="unique"):
            planner.plan(
                _context(tmp_path), (PackageFormat.WHEEL, PackageFormat.WHEEL)
            )


def _write_precondition_project(root: Path) -> None:
    for relative in ("LICENSE", "NOTICE", "COPYRIGHT", "README.md"):
        (root / relative).write_text(relative, encoding="utf-8")
    (root / "pyproject.toml").write_text(
        """
[project]
name = "example"
version = "0.2.0-alpha"
[project.urls]
Homepage = "https://github.com/example/project"
[project.scripts]
ups-engineering = "Engineering.cli.app:app"
[tool.setuptools.package-data]
Engineering = ["config/*.yaml"]
""".strip(),
        encoding="utf-8",
    )
    frontend = root / "Frontend"
    (frontend / "src-tauri").mkdir(parents=True)
    (frontend / "package.json").write_text(
        (
            '{"name":"example","version":"0.2.0-alpha",'
            '"dependencies":{},"devDependencies":{}}'
        ),
        encoding="utf-8",
    )
    (frontend / "package-lock.json").write_text(
        json.dumps(
            {
                "lockfileVersion": 3,
                "packages": {
                    "": {
                        "name": "example",
                        "version": "0.2.0-alpha",
                        "dependencies": {},
                        "devDependencies": {},
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (frontend / "src-tauri" / "tauri.conf.json").write_text(
        '{"version":"0.2.0-alpha"}', encoding="utf-8"
    )
    engineering = root / "Engineering"
    (engineering / "config").mkdir(parents=True)
    (engineering / "core").mkdir()
    (engineering / "config" / "project.yaml").write_text(
        'project:\n  version: "0.2.0-alpha"\n', encoding="utf-8"
    )
    (engineering / "core" / "version.py").write_text(
        'MAJOR = 0\nMINOR = 2\nPATCH = 0\nSTAGE = "alpha"\n', encoding="utf-8"
    )
    build = root / "build"
    build.mkdir()
    steps = [
        {"step_id": step_id, "state": "succeeded"}
        for step_id in (
            "build.validate-project",
            "build.python-syntax",
            "build.backend-inventory",
            "build.frontend-readiness",
        )
    ]
    (build / "build-manifest.json").write_text(
        json.dumps({"steps": steps}), encoding="utf-8"
    )


class TestReleasePreconditions:
    def test_complete_project_passes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _write_precondition_project(tmp_path)
        monkeypatch.setattr("importlib.util.find_spec", lambda name: object())
        monkeypatch.setattr(
            "subprocess.run",
            lambda *args, **kwargs: subprocess.CompletedProcess([], 0, "", ""),
        )

        monkeypatch.setattr("shutil.which", lambda name: "npm")

        report = ReleasePreconditionChecker().check(
            _context(tmp_path),
            (PackageFormat.SDIST, PackageFormat.WHEEL, PackageFormat.FRONTEND_ZIP),
        )

        assert report.passed

    def test_reports_version_mismatch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_precondition_project(tmp_path)
        (tmp_path / "Frontend" / "package.json").write_text(
            '{"version":"0.1.0"}', encoding="utf-8"
        )
        monkeypatch.setattr("importlib.util.find_spec", lambda name: object())
        monkeypatch.setattr(
            "subprocess.run",
            lambda *args, **kwargs: subprocess.CompletedProcess([], 0, "", ""),
        )

        report = ReleasePreconditionChecker().check(
            _context(tmp_path), (PackageFormat.SDIST, PackageFormat.WHEEL)
        )

        assert any(issue.code.startswith("version.mismatch") for issue in report.issues)


def _required_members(prefix: str = "") -> tuple[str, ...]:
    return (
        f"{prefix}Backend/__init__.py",
        f"{prefix}Engineering/__init__.py",
        f"{prefix}Engineering/config/project.yaml",
        f"{prefix}Engineering/Templates/Definitions/project.basic.template.yaml",
    )


class TestPackageInspection:
    def test_inspects_wheel_without_extracting(self, tmp_path: Path) -> None:
        root = tmp_path / "release"
        package = root / "packages" / "python" / "example.whl"
        package.parent.mkdir(parents=True)
        with zipfile.ZipFile(package, mode="w") as archive:
            for name in (*_required_members(), "example.dist-info/METADATA"):
                archive.writestr(name, "content")

        artifact = PackageInspector().inspect(package, root)

        assert artifact.package_format == PackageFormat.WHEEL
        assert artifact.relative_path == "packages/python/example.whl"
        assert artifact.size > 0
        assert len(artifact.sha256) == 64

    def test_inspects_source_distribution(self, tmp_path: Path) -> None:
        root = tmp_path / "release"
        package = root / "packages" / "python" / "example.tar.gz"
        package.parent.mkdir(parents=True)
        names = (
            *_required_members("example/"),
            "example/pyproject.toml",
            "example/LICENSE",
            "example/NOTICE",
        )
        with tarfile.open(package, mode="w:gz") as archive:
            for name in names:
                data = b"content"
                info = tarfile.TarInfo(name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))

        artifact = PackageInspector().inspect(package, root)

        assert artifact.package_format == PackageFormat.SDIST

    def test_rejects_unsafe_or_secret_members(self, tmp_path: Path) -> None:
        root = tmp_path / "release"
        package = root / "unsafe.whl"
        root.mkdir()
        with zipfile.ZipFile(package, mode="w") as archive:
            archive.writestr("../escape", "bad")

        with pytest.raises(ReleaseError, match="Unsafe"):
            PackageInspector().inspect(package, root)

    def test_inspects_frontend_zip(self, tmp_path: Path) -> None:
        root = tmp_path / "release"
        package = root / "packages" / "frontend" / "frontend.zip"
        package.parent.mkdir(parents=True)
        with zipfile.ZipFile(package, mode="w") as archive:
            archive.writestr("index.html", "<div id='app'></div>")
            archive.writestr("assets/app.js", "console.log('ready')")
            archive.writestr("assets/app.css", "body {}")

        artifact = PackageInspector().inspect(package, root)

        assert artifact.package_format == PackageFormat.FRONTEND_ZIP
        assert artifact.relative_path == "packages/frontend/frontend.zip"

    def test_inspects_nsis_windows_executable(self, tmp_path: Path) -> None:
        root = tmp_path / "release"
        package = root / "packages" / "desktop" / "example_x64-setup.exe"
        package.parent.mkdir(parents=True)
        content = bytearray(132)
        content[:2] = b"MZ"
        struct.pack_into("<I", content, 0x3C, 128)
        content[128:132] = b"PE\0\0"
        package.write_bytes(content)

        artifact = PackageInspector().inspect(package, root)

        assert artifact.package_format == PackageFormat.DESKTOP_NSIS
        assert artifact.relative_path == "packages/desktop/example_x64-setup.exe"
        assert artifact.members == ()


class TestFrontendPackageBuilder:
    def test_creates_deterministic_archive(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        frontend = tmp_path / "Frontend"
        frontend.mkdir()
        (frontend / "package.json").write_text(
            '{"name":"frontend","version":"0.2.0-alpha"}', encoding="utf-8"
        )
        (frontend / "package-lock.json").write_text("{}", encoding="utf-8")
        builder = FrontendPackageBuilder()

        def fake_run(command: list[str], cwd: Path, operation: str) -> None:
            if operation == "Vite build":
                assets = cwd / "dist" / "assets"
                assets.mkdir(parents=True, exist_ok=True)
                (cwd / "dist" / "index.html").write_text("index", encoding="utf-8")
                (assets / "app.js").write_text("script", encoding="utf-8")
                (assets / "app.css").write_text("style", encoding="utf-8")

        monkeypatch.setattr("shutil.which", lambda name: "npm")
        monkeypatch.setattr(builder, "_run", fake_run)

        first = builder.build(
            tmp_path, tmp_path / "first", (PackageFormat.FRONTEND_ZIP,)
        )[0].read_bytes()
        second = builder.build(
            tmp_path, tmp_path / "second", (PackageFormat.FRONTEND_ZIP,)
        )[0].read_bytes()

        assert first == second


class TestDesktopPackageBuilder:
    def test_builds_and_stages_nsis_installer(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        frontend = tmp_path / "Frontend"
        tauri = frontend / "src-tauri"
        tauri.mkdir(parents=True)
        (tauri / "Cargo.lock").write_text("version = 4", encoding="utf-8")
        builder = DesktopPackageBuilder()

        def fake_run(
            command: list[str],
            cwd: Path,
            operation: str,
            env: dict[str, str] | None = None,
        ) -> None:
            if operation == "Tauri NSIS build":
                bundle = tauri / "target" / "release" / "bundle" / "nsis"
                bundle.mkdir(parents=True)
                (bundle / "example_x64-setup.exe").write_bytes(b"installer")

        monkeypatch.setattr("shutil.which", lambda name: "npm")
        monkeypatch.setattr(FrontendPackageBuilder, "_run", staticmethod(fake_run))

        artifacts = builder.build(
            tmp_path,
            tmp_path / "packages",
            (PackageFormat.DESKTOP_NSIS,),
        )

        assert len(artifacts) == 1
        assert artifacts[0].name == "example_x64-setup.exe"
        assert artifacts[0].read_bytes() == b"installer"


class TestReleaseManifest:
    def test_round_trip_is_deterministic(self, tmp_path: Path) -> None:
        artifact = PackageArtifact(
            "packages/python/example.whl",
            PackageFormat.WHEEL,
            42,
            "a" * 64,
        )
        manifest = ReleaseManifest(ReleaseVersion("0.2.0-alpha"), (artifact,))
        path = tmp_path / "release-manifest.json"

        manifest.write(path)
        first = path.read_text(encoding="utf-8")
        assert ReleaseManifest.read(path) == manifest
        manifest.write(path)

        assert path.read_text(encoding="utf-8") == first


class TestReleaseReport:
    def test_result_state_is_explicit(self) -> None:
        assert PackageState.SUCCEEDED.value == "succeeded"


class PassingPreconditions:
    def check(
        self,
        context: ReleaseContext,
        formats: tuple[PackageFormat, ...],
    ) -> ReleasePreconditionReport:
        return ReleasePreconditionReport()


class PassingBuildGate:
    def verify(self, context: ReleaseContext) -> tuple[bool, str]:
        return True, "Build succeeded."


class FakePackageBuilder:
    def build(
        self,
        project_root: Path,
        output_directory: Path,
        formats: tuple[PackageFormat, ...],
    ) -> tuple[Path, ...]:
        output_directory.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []
        for package_format in formats:
            names = {
                PackageFormat.SDIST: "example.tar.gz",
                PackageFormat.WHEEL: "example.whl",
                PackageFormat.FRONTEND_ZIP: "frontend.zip",
                PackageFormat.DESKTOP_NSIS: "example_x64-setup.exe",
            }
            name = names[package_format]
            path = output_directory / name
            path.write_bytes(package_format.value.encode())
            paths.append(path)
        return tuple(paths)


class FakeInspector:
    def inspect(self, path: Path, output_root: Path) -> PackageArtifact:
        package_format = (
            PackageFormat.WHEEL
            if path.suffix == ".whl"
            else PackageFormat.DESKTOP_NSIS
            if path.name.endswith("-setup.exe")
            else PackageFormat.FRONTEND_ZIP
            if path.suffix == ".zip"
            else PackageFormat.SDIST
        )
        data = path.read_bytes()
        return PackageArtifact(
            path.relative_to(output_root).as_posix(),
            package_format,
            len(data),
            hashlib.sha256(data).hexdigest(),
        )


class TestReleaseService:
    def test_dry_run_writes_nothing(self, tmp_path: Path) -> None:
        context = _context(tmp_path, dry_run=True)
        service = ReleaseService(
            preconditions=PassingPreconditions(),
            build_gate=PassingBuildGate(),
            builder=FakePackageBuilder(),
            inspector=FakeInspector(),
        )

        execution = service.run(
            context,
            (
                PackageFormat.SDIST,
                PackageFormat.WHEEL,
                PackageFormat.FRONTEND_ZIP,
                PackageFormat.DESKTOP_NSIS,
            ),
        )

        assert execution.report is not None
        assert execution.report.success
        assert all(result.state == PackageState.SKIPPED for result in execution.report.results)
        assert not context.output_root.exists()

    def test_success_writes_packages_checksums_and_manifest(self, tmp_path: Path) -> None:
        context = _context(tmp_path)
        service = ReleaseService(
            preconditions=PassingPreconditions(),
            build_gate=PassingBuildGate(),
            builder=FakePackageBuilder(),
            inspector=FakeInspector(),
        )

        execution = service.run(
            context,
            (
                PackageFormat.SDIST,
                PackageFormat.WHEEL,
                PackageFormat.FRONTEND_ZIP,
                PackageFormat.DESKTOP_NSIS,
            ),
        )

        assert execution.report is not None and execution.report.success
        assert execution.manifest_path is not None and execution.manifest_path.is_file()
        assert execution.checksum_path is not None and execution.checksum_path.is_file()
        assert ReleaseManifest.read(execution.manifest_path) == execution.manifest
        assert len(execution.report.results) == 4
