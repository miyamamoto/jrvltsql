"""Service-key setup guardrails for JV-Link fetchers."""

from unittest.mock import MagicMock

from src.fetcher.base import BaseFetcher


class DummyFetcher(BaseFetcher):
    def fetch(self, **kwargs):
        return iter(())


def _fetcher_with(jvlink, service_key="TEST-KEY"):
    fetcher = DummyFetcher.__new__(DummyFetcher)
    fetcher.jvlink = jvlink
    fetcher._service_key = service_key
    return fetcher


def test_configure_service_key_skips_wine_by_default(monkeypatch):
    monkeypatch.delenv("JVLINK_SET_SERVICE_KEY", raising=False)
    jvlink = MagicMock()
    jvlink.uses_wine = True
    fetcher = _fetcher_with(jvlink)

    fetcher._configure_service_key()

    jvlink.jv_set_service_key.assert_not_called()


def test_configure_service_key_allows_wine_with_opt_in(monkeypatch):
    monkeypatch.setenv("JVLINK_SET_SERVICE_KEY", "1")
    jvlink = MagicMock()
    jvlink.uses_wine = True
    jvlink.jv_set_service_key.return_value = 0
    fetcher = _fetcher_with(jvlink)

    fetcher._configure_service_key()

    jvlink.jv_set_service_key.assert_called_once_with("TEST-KEY")


def test_configure_service_key_keeps_non_wine_behavior(monkeypatch):
    monkeypatch.delenv("JVLINK_SET_SERVICE_KEY", raising=False)
    jvlink = MagicMock()
    jvlink.uses_wine = False
    jvlink.jv_set_service_key.return_value = 0
    fetcher = _fetcher_with(jvlink)

    fetcher._configure_service_key()

    jvlink.jv_set_service_key.assert_called_once_with("TEST-KEY")
