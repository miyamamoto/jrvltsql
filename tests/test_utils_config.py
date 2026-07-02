"""Unit tests for src/utils/config.py."""

import os
from pathlib import Path

import pytest
import yaml

from src.utils.config import (
    Config,
    ConfigError,
    _expand_env_vars,
    _validate_config,
    get_default_config,
    load_config,
)


# ---------------------------------------------------------------------------
# Config.get
# ---------------------------------------------------------------------------

class TestConfigGet:
    def _cfg(self):
        return Config({
            "jvlink": {"service_key": "ABC123456789", "sid": "TEST"},
            "databases": {"sqlite": {"enabled": True, "path": "./test.db"}},
            "nested": {"a": {"b": {"c": 42}}},
        })

    def test_simple_key(self):
        assert self._cfg().get("nested") == {"a": {"b": {"c": 42}}}

    def test_dotted_key(self):
        assert self._cfg().get("jvlink.service_key") == "ABC123456789"

    def test_deeply_nested(self):
        assert self._cfg().get("nested.a.b.c") == 42

    def test_missing_key_returns_default(self):
        assert self._cfg().get("missing.key") is None
        assert self._cfg().get("missing.key", "fallback") == "fallback"

    def test_missing_mid_path_returns_default(self):
        assert self._cfg().get("jvlink.nonexistent.sub") is None

    def test_getitem_existing(self):
        assert self._cfg()["jvlink.sid"] == "TEST"

    def test_getitem_missing_raises(self):
        with pytest.raises(KeyError):
            _ = self._cfg()["does.not.exist"]

    def test_to_dict(self):
        cfg = self._cfg()
        d = cfg.to_dict()
        assert isinstance(d, dict)
        assert d["jvlink"]["service_key"] == "ABC123456789"


# ---------------------------------------------------------------------------
# _expand_env_vars
# ---------------------------------------------------------------------------

class TestExpandEnvVars:
    def test_simple_env_var(self, monkeypatch):
        monkeypatch.setenv("MY_KEY", "secret123")
        result = _expand_env_vars("${MY_KEY}")
        assert result == "secret123"

    def test_missing_env_var_uses_default(self):
        result = _expand_env_vars("${NONEXISTENT_VAR:fallback}")
        assert result == "fallback"

    def test_missing_env_var_no_default_empty(self):
        result = _expand_env_vars("${DEFINITELY_NOT_SET_XYZ}")
        assert result == ""

    def test_empty_default_is_supported(self):
        result = _expand_env_vars("${DEFINITELY_NOT_SET_XYZ:}")
        assert result == ""

    def test_nested_dict(self, monkeypatch):
        monkeypatch.setenv("HOST", "localhost")
        result = _expand_env_vars({"db": {"host": "${HOST}"}})
        assert result["db"]["host"] == "localhost"

    def test_list(self, monkeypatch):
        monkeypatch.setenv("ITEM", "value")
        result = _expand_env_vars(["${ITEM}", "literal"])
        assert result == ["value", "literal"]

    def test_non_string_passthrough(self):
        assert _expand_env_vars(42) == 42
        assert _expand_env_vars(True) is True
        assert _expand_env_vars(None) is None

    def test_inline_expansion(self, monkeypatch):
        monkeypatch.setenv("PORT", "5432")
        result = _expand_env_vars("postgres://host:${PORT}/db")
        assert result == "postgres://host:5432/db"


# ---------------------------------------------------------------------------
# _validate_config
# ---------------------------------------------------------------------------

class TestValidateConfig:
    def _valid(self):
        return {
            "jvlink": {"service_key": "VALIDKEY123"},
            "databases": {"sqlite": {"enabled": True}},
        }

    def test_valid_config_passes(self):
        _validate_config(self._valid())  # should not raise

    def test_missing_jvlink_raises(self):
        cfg = self._valid()
        del cfg["jvlink"]
        with pytest.raises(ConfigError, match="jvlink"):
            _validate_config(cfg)

    def test_missing_databases_raises(self):
        cfg = self._valid()
        del cfg["databases"]
        with pytest.raises(ConfigError, match="databases"):
            _validate_config(cfg)

    def test_no_enabled_db_raises(self):
        cfg = self._valid()
        cfg["databases"]["sqlite"]["enabled"] = False
        with pytest.raises(ConfigError, match="At least one"):
            _validate_config(cfg)

    def test_short_service_key_raises(self):
        cfg = self._valid()
        cfg["jvlink"]["service_key"] = "short"
        with pytest.raises(ConfigError, match="service key"):
            _validate_config(cfg)

    def test_env_var_service_key_skips_length_check(self):
        cfg = self._valid()
        cfg["jvlink"]["service_key"] = "${JVLINK_KEY}"
        _validate_config(cfg)  # should not raise

    def test_empty_service_key_skips_check(self):
        cfg = self._valid()
        cfg["jvlink"]["service_key"] = ""
        _validate_config(cfg)  # empty is allowed (env var path)


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def _write_yaml(self, tmp_path: Path, content: dict) -> Path:
        p = tmp_path / "config.yaml"
        p.write_text(yaml.dump(content), encoding="utf-8")
        return p

    def test_load_valid_config(self, tmp_path):
        path = self._write_yaml(tmp_path, {
            "jvlink": {"service_key": "TESTKEY12345"},
            "databases": {"sqlite": {"enabled": True, "path": "./test.db"}},
        })
        cfg = load_config(path)
        assert cfg.get("jvlink.service_key") == "TESTKEY12345"

    def test_load_missing_file_raises(self, tmp_path):
        with pytest.raises(ConfigError, match="not found"):
            load_config(tmp_path / "missing.yaml")

    def test_load_empty_file_raises(self, tmp_path):
        p = tmp_path / "empty.yaml"
        p.write_text("", encoding="utf-8")
        with pytest.raises(ConfigError, match="empty"):
            load_config(p)

    def test_load_invalid_yaml_raises(self, tmp_path):
        p = tmp_path / "bad.yaml"
        p.write_text("jvlink: {\n  unclosed", encoding="utf-8")
        with pytest.raises(ConfigError, match="YAML"):
            load_config(p)

    def test_load_expands_env_vars(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TEST_SK", "ENVKEY12345678")
        path = self._write_yaml(tmp_path, {
            "jvlink": {"service_key": "${TEST_SK}"},
            "databases": {"sqlite": {"enabled": True}},
        })
        cfg = load_config(path)
        assert cfg.get("jvlink.service_key") == "ENVKEY12345678"

    def test_postgres_url_env_overrides_config_and_generic_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv(
            "JRVLTSQL_POSTGRES_URL",
            "postgresql://writer:p%40ss@postgres:15432/keiba_staging?sslmode=require",
        )
        monkeypatch.setenv("POSTGRES_USER", "etl_readonly")
        path = self._write_yaml(tmp_path, {
            "jvlink": {"service_key": "TESTKEY12345"},
            "database": {"type": "postgresql"},
            "databases": {
                "postgresql": {
                    "enabled": True,
                    "host": "localhost",
                    "port": 5432,
                    "database": "keiba",
                    "user": "postgres",
                    "password": "",
                }
            },
        })

        cfg = load_config(path)

        assert cfg.get("databases.postgresql.host") == "postgres"
        assert cfg.get("databases.postgresql.port") == 15432
        assert cfg.get("databases.postgresql.database") == "keiba_staging"
        assert cfg.get("databases.postgresql.user") == "writer"
        assert cfg.get("databases.postgresql.password") == "p@ss"
        assert cfg.get("databases.postgresql.sslmode") == "require"

    def test_postgres_standard_env_overrides_config_without_url(self, tmp_path, monkeypatch):
        monkeypatch.delenv("JRVLTSQL_POSTGRES_URL", raising=False)
        monkeypatch.delenv("POSTGRES_URL", raising=False)
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("PGHOST", "pg-host")
        monkeypatch.setenv("PGPORT", "25432")
        monkeypatch.setenv("PGDATABASE", "pg_db")
        monkeypatch.setenv("PGUSER", "pg_user")
        monkeypatch.setenv("PGPASSWORD", "pg_pass")
        path = self._write_yaml(tmp_path, {
            "jvlink": {"service_key": "TESTKEY12345"},
            "database": {"type": "postgresql"},
            "databases": {
                "postgresql": {
                    "enabled": True,
                    "host": "localhost",
                    "port": 5432,
                    "database": "keiba",
                    "user": "postgres",
                    "password": "",
                }
            },
        })

        cfg = load_config(path)

        assert cfg.get("databases.postgresql.host") == "pg-host"
        assert cfg.get("databases.postgresql.port") == 25432
        assert cfg.get("databases.postgresql.database") == "pg_db"
        assert cfg.get("databases.postgresql.user") == "pg_user"
        assert cfg.get("databases.postgresql.password") == "pg_pass"

    def test_load_invalid_config_raises(self, tmp_path):
        path = self._write_yaml(tmp_path, {"only": "jvlink_missing"})
        with pytest.raises(ConfigError):
            load_config(path)


# ---------------------------------------------------------------------------
# get_default_config
# ---------------------------------------------------------------------------

class TestGetDefaultConfig:
    def test_returns_dict(self):
        d = get_default_config()
        assert isinstance(d, dict)

    def test_has_required_sections(self):
        d = get_default_config()
        assert "jvlink" in d
        assert "databases" in d
        assert "logging" in d

    def test_sqlite_enabled_by_default(self):
        d = get_default_config()
        assert d["databases"]["sqlite"]["enabled"] is True

    def test_returns_new_copy_each_time(self):
        d1 = get_default_config()
        d2 = get_default_config()
        d1["jvlink"]["service_key"] = "MODIFIED"
        assert d2["jvlink"]["service_key"] == ""
