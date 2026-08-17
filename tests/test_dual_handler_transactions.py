from unittest.mock import MagicMock

import pytest

from src.database.base import DatabaseError
from src.database.dual_handler import DualDatabase


def _dual_database():
    primary = MagicMock()
    secondary = MagicMock()
    primary.get_db_type.return_value = "sqlite"
    secondary.get_db_type.return_value = "postgresql"
    primary.has_pending_transaction.return_value = False
    secondary.has_pending_transaction.return_value = False
    secondary.is_connected.return_value = True
    return DualDatabase(primary, secondary), primary, secondary


def test_dual_transaction_begins_and_rolls_back_both_backends():
    database, primary, secondary = _dual_database()

    database.begin_transaction()
    first_generation = database.get_transaction_generation()
    assert first_generation is not None
    database.rollback()
    assert database.get_transaction_generation() is None

    database.begin_transaction()
    assert database.get_transaction_generation() == first_generation + 1
    database.rollback()

    assert primary.begin_transaction.call_count == 2
    assert secondary.begin_transaction.call_count == 2
    assert primary.rollback.call_count == 2
    assert secondary.rollback.call_count == 2
    assert not database._transaction_active


def test_dual_pending_transaction_uses_either_connected_backend():
    database, primary, secondary = _dual_database()

    assert database.has_pending_transaction() is False
    primary.has_pending_transaction.return_value = True
    assert database.has_pending_transaction() is True
    primary.has_pending_transaction.return_value = False
    secondary.has_pending_transaction.return_value = True
    assert database.has_pending_transaction() is True

    secondary.has_pending_transaction.side_effect = DatabaseError(
        "transaction state unavailable"
    )
    with pytest.raises(DatabaseError, match="transaction state unavailable"):
        database.has_pending_transaction()


def test_dual_transaction_secondary_write_failure_is_not_swallowed():
    database, primary, secondary = _dual_database()
    secondary.insert_many.side_effect = RuntimeError("mirror unavailable")
    database.begin_transaction()

    with pytest.raises(DatabaseError, match="secondary insert_many failed"):
        database.insert_many("RT_RA", [{"Year": 2026}])

    assert not database.secondary_in_sync
    database.rollback()
    primary.rollback.assert_called_once_with()
    secondary.rollback.assert_called_once_with()


def test_dual_transaction_mirrors_raw_delete_to_both_backends():
    database, primary, secondary = _dual_database()
    database.begin_transaction()

    database.execute("DELETE FROM RT_RA WHERE Year = ?", (2026,))

    primary.execute.assert_called_once_with(
        "DELETE FROM RT_RA WHERE Year = ?", (2026,)
    )
    secondary.execute.assert_called_once_with(
        "DELETE FROM RT_RA WHERE Year = ?", (2026,)
    )


def test_dual_transaction_secondary_raw_delete_failure_is_not_swallowed():
    database, primary, secondary = _dual_database()
    secondary.execute.side_effect = RuntimeError("mirror unavailable")
    database.begin_transaction()

    with pytest.raises(DatabaseError, match="secondary execute failed"):
        database.execute("DELETE FROM RT_RA WHERE Year = ?", (2026,))

    database.rollback()
    primary.rollback.assert_called_once_with()
    secondary.rollback.assert_called_once_with()


def test_dual_transaction_mirrors_executemany_and_propagates_failure():
    database, primary, secondary = _dual_database()
    secondary.executemany.side_effect = RuntimeError("mirror unavailable")
    database.begin_transaction()

    with pytest.raises(DatabaseError, match="secondary executemany failed"):
        database.executemany(
            "UPDATE RT_RA SET DataKubun = ? WHERE Year = ?",
            [("9", 2026)],
        )

    primary.executemany.assert_called_once_with(
        "UPDATE RT_RA SET DataKubun = ? WHERE Year = ?",
        [("9", 2026)],
    )


def test_dual_secondary_begin_failure_rolls_back_primary():
    database, primary, secondary = _dual_database()
    secondary.begin_transaction.side_effect = RuntimeError("begin failed")

    with pytest.raises(DatabaseError, match="secondary begin failed"):
        database.begin_transaction()

    primary.rollback.assert_called_once_with()
    assert not database._transaction_active


def test_dual_secondary_commit_failure_marks_mirror_out_of_sync():
    database, primary, secondary = _dual_database()
    secondary.commit.side_effect = RuntimeError("commit outcome unknown")
    database.begin_transaction()

    database.commit()

    primary.commit.assert_called_once_with()
    secondary.commit.assert_called_once_with()
    assert not database.secondary_in_sync
    assert not database._transaction_active
