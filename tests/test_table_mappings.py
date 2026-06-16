#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for JRA-VAN table name mappings."""

from src.database.table_mappings import (
    JLTSQL_TO_JRAVAN,
    JRAVAN_TO_JLTSQL,
    RECORD_TYPE_TO_TABLE,
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
        "O1": ("NL_O1", "ODDS_TANPUKU"),
        "O2": ("NL_O2", "ODDS_UMAREN"),
        "O3": ("NL_O3", "ODDS_WIDE"),
        "O4": ("NL_O4", "ODDS_UMATAN"),
        "O5": ("NL_O5", "ODDS_SANRENPUKU"),
        "O6": ("NL_O6", "ODDS_SANRENTAN"),
    }
    for record_type, (table_name, jravan_name) in expected_odds.items():
        assert RECORD_TYPE_TO_TABLE[record_type] == table_name
        assert JRAVAN_TO_JLTSQL[jravan_name] == table_name
        assert JLTSQL_TO_JRAVAN[table_name] == jravan_name

    assert RECORD_TYPE_TO_TABLE["H1"] == "NL_H1"
    assert RECORD_TYPE_TO_TABLE["H6"] == "NL_H6"
    assert JRAVAN_TO_JLTSQL["HYO_TANPUKU"] == "NL_H1"
    assert JRAVAN_TO_JLTSQL["HYO_SANRENTAN"] == "NL_H6"
