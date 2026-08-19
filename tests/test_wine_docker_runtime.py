"""Wine/Docker ランタイム層の契約テスト。

JV-Link のインストール・利用規約への同意・サービスキー登録は人の意思表示なので、
このリポジトリは自動化しない。イメージと起動スクリプトがその境界を守っていること、
および 32-bit 前提を fail closed で守っていることを固定する。
"""

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE = ROOT / "Dockerfile"
COMPOSE = ROOT / "docker-compose.yml"
ENTRYPOINT = ROOT / "scripts" / "docker-entrypoint.sh"
BRIDGE_SOURCE = ROOT / "tools" / "jvlink-bridge" / "bridge_native.c"
MANUAL_GUIDE = ROOT / "docs" / "jvlink_manual_registration.md"

APPROVAL_AUTOMATION = (
    "setup_wine_jvlink",
    "AUTO_INSTALL_JVLINK",
    "JVLINK_AUTO_ACCEPT_TERMS",
    "AUTO_DISMISS_JVLINK_DIALOGS",
    "JVLINK_FORCE_RESET_REGISTRATION",
    "RESET_REGISTRATION_ON_KEY_CHANGE",
    "jv_set_service_key",
    "JVLINK_SET_SERVICE_KEY",
)


@pytest.mark.parametrize(
    "path", (DOCKERFILE, COMPOSE, ENTRYPOINT), ids=lambda path: path.name
)
def test_runtime_files_exist(path: Path) -> None:
    assert path.is_file()


@pytest.mark.parametrize(
    "path", (DOCKERFILE, COMPOSE, ENTRYPOINT), ids=lambda path: path.name
)
@pytest.mark.parametrize("token", APPROVAL_AUTOMATION)
def test_runtime_never_automates_approval(path: Path, token: str) -> None:
    """規約同意・キー登録を機械が代行する経路を置かない。"""

    assert token not in path.read_text(encoding="utf-8")


def test_compose_declares_no_service_key() -> None:
    compose = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    environment = compose["services"]["jltsql"]["environment"]
    assert not [name for name in environment if "SERVICE_KEY" in name]


def test_image_declares_the_external_bridge_runner() -> None:
    """非 Windows では runner を推測しないので、イメージが宣言しないと動かない。"""

    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    assert "ENV JVLINK_BRIDGE_RUNNER=wine" in dockerfile
    compose = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    assert compose["services"]["jltsql"]["environment"]["JVLINK_BRIDGE_RUNNER"] == "wine"


def test_image_reaps_wine_children() -> None:
    """Wine の子プロセスを回収する PID 1 が無いとゾンビが溜まり続ける。"""

    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    assert "        tini \\" in dockerfile
    assert 'ENTRYPOINT ["/usr/bin/tini", "--", "scripts/docker-entrypoint.sh"]' in dockerfile


def test_prefix_is_initialized_without_a_display() -> None:
    """X 表示が見えると win64 prefix の 32-bit 側が作られない。"""

    entrypoint = ENTRYPOINT.read_text(encoding="utf-8")
    assert "env -u DISPLAY" in entrypoint
    assert "wineboot --init" in entrypoint


def test_missing_32bit_support_fails_closed() -> None:
    entrypoint = ENTRYPOINT.read_text(encoding="utf-8")
    assert "syswow64/kernel32.dll" in entrypoint.replace('"', "")
    assert "verify_wine_prefix || exit 1" in entrypoint


def test_manual_guide_covers_the_human_steps() -> None:
    guide = MANUAL_GUIDE.read_text(encoding="utf-8")
    for required in (
        "6080/vnc.html",  # noVNC を開く
        "wine /installers/",  # インストーラを人が起動する
        "サービスキーを入力",  # 登録は人が行う
        "ダウンロードしますか",  # 版更新ダイアログは人が答える
    ):
        assert required in guide


def test_bridge_source_is_shipped_for_the_image_build() -> None:
    assert BRIDGE_SOURCE.is_file()
    assert "CoCreateInstance" in BRIDGE_SOURCE.read_text(
        encoding="utf-8", errors="replace"
    )
