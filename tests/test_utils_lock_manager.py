"""Unit tests for src/utils/lock_manager.py."""

import os
import sys
from pathlib import Path

import pytest

from src.utils.lock_manager import ProcessLock, ProcessLockError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _lock(tmp_path: Path, name: str = "test", timeout: int = 0) -> ProcessLock:
    return ProcessLock(name, lock_dir=tmp_path / ".locks", timeout=timeout)


# ---------------------------------------------------------------------------
# Basic acquire / release
# ---------------------------------------------------------------------------

class TestAcquireRelease:
    def test_acquire_returns_true(self, tmp_path):
        lock = _lock(tmp_path)
        assert lock.acquire() is True
        lock.release()

    def test_lock_file_created_on_acquire(self, tmp_path):
        lock = _lock(tmp_path)
        lock.acquire()
        assert lock.lock_file.exists()
        lock.release()

    def test_lock_file_contains_current_pid(self, tmp_path):
        lock = _lock(tmp_path)
        lock.acquire()
        pid = int(lock.lock_file.read_text())
        assert pid == os.getpid()
        lock.release()

    def test_lock_file_removed_on_release(self, tmp_path):
        lock = _lock(tmp_path)
        lock.acquire()
        lock.release()
        assert not lock.lock_file.exists()

    def test_double_release_is_safe(self, tmp_path):
        lock = _lock(tmp_path)
        lock.acquire()
        lock.release()
        lock.release()  # should not raise

    def test_release_without_acquire_is_safe(self, tmp_path):
        lock = _lock(tmp_path)
        lock.release()  # should not raise


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

class TestConflict:
    def test_second_acquire_raises_when_locked(self, tmp_path):
        lock1 = _lock(tmp_path, "mylock")
        lock2 = _lock(tmp_path, "mylock")
        lock1.acquire()
        try:
            with pytest.raises(ProcessLockError, match="already running"):
                lock2.acquire()
        finally:
            lock1.release()

    def test_different_names_do_not_conflict(self, tmp_path):
        lock_a = _lock(tmp_path, "alpha")
        lock_b = _lock(tmp_path, "beta")
        lock_a.acquire()
        lock_b.acquire()  # should succeed
        lock_a.release()
        lock_b.release()

    def test_acquire_after_release_succeeds(self, tmp_path):
        lock1 = _lock(tmp_path, "reuse")
        lock2 = _lock(tmp_path, "reuse")
        lock1.acquire()
        lock1.release()
        assert lock2.acquire() is True
        lock2.release()


# ---------------------------------------------------------------------------
# Stale lock cleanup
# ---------------------------------------------------------------------------

class TestStaleLock:
    def test_stale_lock_removed_on_acquire(self, tmp_path):
        lock_dir = tmp_path / ".locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        stale = lock_dir / "staletest.lock"
        stale.write_text("99999999")  # non-existent PID

        lock = ProcessLock("staletest", lock_dir=lock_dir)
        assert lock.acquire() is True
        lock.release()

    def test_invalid_lock_file_removed_on_acquire(self, tmp_path):
        lock_dir = tmp_path / ".locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        bad = lock_dir / "badlock.lock"
        bad.write_text("not_a_pid")

        lock = ProcessLock("badlock", lock_dir=lock_dir)
        assert lock.acquire() is True
        lock.release()


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

class TestContextManager:
    def test_context_manager_acquires_and_releases(self, tmp_path):
        lock = _lock(tmp_path, "ctx")
        with lock:
            assert lock.lock_file.exists()
        assert not lock.lock_file.exists()

    def test_context_manager_releases_on_exception(self, tmp_path):
        lock = _lock(tmp_path, "ctx_exc")
        try:
            with lock:
                assert lock.lock_file.exists()
                raise ValueError("boom")
        except ValueError:
            pass
        assert not lock.lock_file.exists()

    def test_context_manager_blocks_second_entry(self, tmp_path):
        lock1 = _lock(tmp_path, "block")
        lock2 = _lock(tmp_path, "block")
        with lock1:
            with pytest.raises(ProcessLockError):
                lock2.__enter__()

    def test_nested_same_lock_raises(self, tmp_path):
        lock = _lock(tmp_path, "nested")
        with lock:
            with pytest.raises(ProcessLockError):
                lock.acquire()


# ---------------------------------------------------------------------------
# Lock directory creation
# ---------------------------------------------------------------------------

class TestLockDir:
    def test_lock_dir_created_automatically(self, tmp_path):
        lock_dir = tmp_path / "deep" / "nested" / ".locks"
        assert not lock_dir.exists()
        lock = ProcessLock("dirtest", lock_dir=lock_dir)
        assert lock_dir.exists()

    def test_lock_file_name_matches_lock_name(self, tmp_path):
        lock = _lock(tmp_path, "myprocess")
        lock.acquire()
        assert (tmp_path / ".locks" / "myprocess.lock").exists()
        lock.release()
