"""Self-update is disabled by default on this fork; CN mirrors are opt-in."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from click.testing import CliRunner

from octop.api.routers import update as update_router
from octop.infra.errors import OctopError
from octop.infra.setup import self_update


@pytest.fixture(autouse=True)
def _default_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("OCTOP_DISABLE_SELF_UPDATE", "OCTOP_USE_CN_MIRRORS", "OCTOP_PYPI_MIRRORS"):
        monkeypatch.delenv(key, raising=False)


def _server() -> Any:
    class Repo:
        def get(self, _key: str) -> None:
            return None

        def set(self, _key: str, _value: str) -> None:
            return None

    return type("Server", (), {"services": type("Svc", (), {"settings_repo": Repo()})()})()


def test_self_update_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    assert self_update.self_update_disabled() is True
    monkeypatch.setenv("OCTOP_DISABLE_SELF_UPDATE", "false")
    assert self_update.self_update_disabled() is False
    monkeypatch.setenv("OCTOP_DISABLE_SELF_UPDATE", "1")
    assert self_update.self_update_disabled() is True


def test_run_upgrade_refuses_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(**_: object) -> None:
        raise AssertionError("installer must not run")

    monkeypatch.setattr(self_update, "_run_managed_upgrade", boom)
    result = self_update.run_upgrade()
    assert result.success is False
    assert "managed by its deployer" in (result.error or "")


def test_status_and_check_skip_pypi_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_pypi() -> None:
        raise AssertionError("PyPI must not be contacted")

    monkeypatch.setattr(update_router, "fetch_pypi_info", no_pypi)
    status = asyncio.run(update_router.update_status(_=None, server=_server()))
    assert status["managed_by_deployer"] is True
    assert status["has_update"] is False
    assert status["latest_version"] is None
    assert "OCTOP_DISABLE_SELF_UPDATE" in status["managed_message"]
    checked = asyncio.run(update_router.check_for_updates(_=None, server=_server()))
    assert checked["managed_by_deployer"] is True


def test_trigger_upgrade_forbidden_when_disabled() -> None:
    with pytest.raises(OctopError):
        asyncio.run(
            update_router.trigger_upgrade(
                body=update_router.UpgradeBody(), server=_server(), _=None
            )
        )


def test_cli_update_reports_managed(monkeypatch: pytest.MonkeyPatch) -> None:
    from octop.cli.main import cli

    monkeypatch.setattr(self_update, "fetch_pypi_info", lambda: None)
    result = CliRunner().invoke(cli, ["update", "--check"])
    assert result.exit_code == 0
    assert "managed by its deployer" in result.output
    result = CliRunner().invoke(cli, ["update", "--yes"])
    assert result.exit_code == 1


def test_pypi_mirrors_default_to_official_only(monkeypatch: pytest.MonkeyPatch) -> None:
    assert self_update.pypi_mirrors() == []
    probed: list[str] = []

    def fake_probe(index_url: str, **_: object) -> self_update.IndexProbe:
        probed.append(index_url)
        return self_update.IndexProbe(index_url, "pypi.org", 0.01, "has_version")

    monkeypatch.setattr(self_update, "probe_index", fake_probe)
    ordered, _skips = self_update.rank_install_indexes("1.0.0")
    assert ordered == [("https://pypi.org/simple", "pypi.org")]
    assert probed == ["https://pypi.org/simple"]

    monkeypatch.setenv("OCTOP_USE_CN_MIRRORS", "1")
    assert any("aliyun" in url for url in self_update.pypi_mirrors())
    monkeypatch.setenv("OCTOP_PYPI_MIRRORS", "https://pypi.example.com/simple/")
    assert self_update.pypi_mirrors() == ["https://pypi.example.com/simple"]
