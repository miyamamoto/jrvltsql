#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for JRA-VAN table name mappings."""

from src.database.table_mappings import (
    JLTSQL_TO_JRAVAN,
    JRAVAN_TO_JLTSQL,
    RECORD_TYPE_TO_TABLE,
    STANDARD_EXPANDED_RECORD_OWNER,
)


def test_training_sale_odds_and_vote_mappings():
    """Critical record/table mappings should match JRA-VAN data semantics."""

    assert JRAVAN_TO_JLTSQL["HANRO"] == "NL_HC"
    assert JRAVAN_TO_JLTSQL["SALE"] == "NL_HS"
    assert RECORD_TYPE_TO_TABLE["HC"] == "NL_HC"
    assert RECORD_TYPE_TO_TABLE["HS"] == "NL_HS"
    assert JLTSQL_TO_JRAVAN["NL_HC"] == "HANRO"
    assert JLTSQL_TO_JRAVAN["NL_HS"] == "SALE"

    expected_odds = {
        "O1": ("NL_O1", "ODDS_TANPUKU", "ODDS_TANPUKUWAKU_HEAD"),
        "O2": ("NL_O2", "ODDS_UMAREN", "ODDS_UMAREN_HEAD"),
        "O3": ("NL_O3", "ODDS_WIDE", "ODDS_WIDE_HEAD"),
        "O4": ("NL_O4", "ODDS_UMATAN", "ODDS_UMATAN_HEAD"),
        "O5": ("NL_O5", "ODDS_SANRENPUKU", "ODDS_SANREN_HEAD"),
        "O6": ("NL_O6", "ODDS_SANRENTAN", "ODDS_SANRENTAN_HEAD"),
    }
    for record_type, (table_name, jravan_name, owner_name) in expected_odds.items():
        assert RECORD_TYPE_TO_TABLE[record_type] == table_name
        assert JRAVAN_TO_JLTSQL[jravan_name] == table_name
        assert JLTSQL_TO_JRAVAN[table_name] == jravan_name
        assert STANDARD_EXPANDED_RECORD_OWNER[table_name] == owner_name

    assert JRAVAN_TO_JLTSQL["ODDS_TANPUKU"] == "NL_O1"
    assert JRAVAN_TO_JLTSQL["ODDS_WAKU"] == "NL_O1"
    assert JRAVAN_TO_JLTSQL["ODDS_SANREN"] == "NL_O5"
    assert JRAVAN_TO_JLTSQL["ODDS_SANRENPUKU"] == "NL_O5"

    assert RECORD_TYPE_TO_TABLE["H1"] == "NL_H1"
    assert RECORD_TYPE_TO_TABLE["H6"] == "NL_H6"
    for standard_name in (
        "HYOSU",
        "HYOSU_TANPUKU",
        "HYOSU_WAKU",
        "HYOSU_UMARENWIDE",
        "HYOSU_UMATAN",
        "HYOSU_SANREN",
    ):
        assert JRAVAN_TO_JLTSQL[standard_name] == "NL_H1"
    for standard_name in ("HYOSU2", "HYOSU_SANRENTAN"):
        assert JRAVAN_TO_JLTSQL[standard_name] == "NL_H6"
    assert JRAVAN_TO_JLTSQL["HYO_TANPUKU"] == "NL_H1"
    assert JRAVAN_TO_JLTSQL["HYO_SANRENTAN"] == "NL_H6"
    assert JLTSQL_TO_JRAVAN["NL_H1"] == "HYO_TANPUKU"
    assert JLTSQL_TO_JRAVAN["NL_H6"] == "HYO_SANRENTAN"
    assert STANDARD_EXPANDED_RECORD_OWNER["NL_H1"] == "HYOSU"
    assert STANDARD_EXPANDED_RECORD_OWNER["NL_H6"] == "HYOSU2"
