"""Tests for JV-Link return code constants and error messages.

Regression coverage for PR #144 review follow-ups:
- -100 lacked a named constant despite being referenced in ERROR_MESSAGES
  and in comments in src/jvlink/wrapper.py (CodeRabbit).
- -2 means "setup dialog canceled" for JVOpen but "error" for JVRead; the
  message only documented the JVOpen meaning (Gemini).
- -111/-114/-115 are documented as parameter errors per the official spec,
  but SUBSCRIPTION_ERROR_CODES (scripts/quickstart.py, scripts/daily_update.py,
  scripts/background_updater.py, src/services/realtime_monitor.py) treats the
  same codes as "unsubscribed data type, skip" based on empirically observed
  production behavior (commit bf69cb6). The messages must document both
  meanings so a reader doesn't assume the official-spec wording is exhaustive
  (Codex).

Verified directly against the official JV-Link4901.pdf ("3. コード表",
Ver.4.9.0.1, 2024/8/7, https://jra-van.jp/dlb/sdv/sdk/JV-Link4901.pdf) rather
than the PR description alone: -100 was correctly valued but grouped under a
"Parameter Errors (JVOpen/JVRTOpen)" comment alongside -111..-116 by the
initial follow-up fix, which is wrong -- the spec's JVOpen/JVRTOpen table has
no -100 entry at all; -100 belongs to JVSetUIProperties/JVSetServiceKey/
JVSetSaveFlag/JVSetSavePath. Corrected here.
"""

from src.jvlink.constants import (
    ERROR_MESSAGES,
    JV_RT_INVALID_DATASPEC,
    JV_RT_INVALID_KEY,
    JV_RT_INVALID_OPTION,
    JV_RT_INVALID_PARAMETER,
    JV_RT_SETUP_CANCELED,
    JV_READ_ERROR,
    get_error_message,
)


def test_invalid_parameter_constant_matches_error_message():
    assert JV_RT_INVALID_PARAMETER == -100
    assert get_error_message(-100) == ERROR_MESSAGES[-100]
    assert "パラメータ" in get_error_message(-100)


def test_invalid_parameter_is_not_mislabeled_as_jvopen():
    # Per the official spec ("3. コード表", JV-Link4901.pdf), -100 is returned
    # by JVSetUIProperties/JVSetServiceKey/JVSetSaveFlag/JVSetSavePath, never
    # by JVOpen/JVRTOpen (whose parameter errors start at -111). Guards
    # against re-introducing the earlier miscategorization, where -100 was
    # grouped under a "Parameter Errors (JVOpen/JVRTOpen)" comment alongside
    # -111..-116.
    message = get_error_message(-100)
    assert "の戻り値ではない" in message
    assert "JVSetServiceKey" in message


def test_setup_canceled_documents_both_jvopen_and_jvread_meanings():
    # -2 means "setup dialog canceled" for JVOpen but JV_READ_ERROR for JVRead;
    # JV_RT_SETUP_CANCELED and JV_READ_ERROR are the same numeric code.
    assert JV_RT_SETUP_CANCELED == JV_READ_ERROR == -2

    message = get_error_message(-2)
    assert "JVOpen" in message
    assert "JVRead" in message


def test_subscription_prone_codes_document_dual_meaning():
    # These three codes are empirically overloaded: official-spec parameter
    # error vs. observed "unsubscribed data type" in production. See
    # SUBSCRIPTION_ERROR_CODES in scripts/quickstart.py and
    # src/services/realtime_monitor.py, which intentionally treat them as
    # skip-worthy regardless of the official-spec wording.
    for code in (JV_RT_INVALID_DATASPEC, JV_RT_INVALID_KEY, JV_RT_INVALID_OPTION):
        message = get_error_message(code)
        assert "未購読" in message, f"code {code} message missing dual-meaning note: {message}"


def test_subscription_error_codes_match_documented_dual_meaning_codes():
    # Guards against SUBSCRIPTION_ERROR_CODES silently drifting away from the
    # codes constants.py documents as having this dual meaning (or vice versa).
    from scripts.quickstart import SUBSCRIPTION_ERROR_CODES

    assert SUBSCRIPTION_ERROR_CODES == frozenset(
        {JV_RT_INVALID_DATASPEC, JV_RT_INVALID_KEY, JV_RT_INVALID_OPTION}
    )


def test_get_error_message_unknown_code_is_explicit():
    assert "不明なエラーコード" in get_error_message(-999999)
