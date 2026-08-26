"""Test-only Click runner compatibility helpers."""

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager

from click.testing import CliRunner as ClickCliRunner


class CliRunner(ClickCliRunner):
    """Keep CLI tests isolated without Click's deprecated CWD helper."""

    @contextmanager
    def isolated_filesystem(self) -> Iterator[str]:
        original_directory = os.getcwd()
        with tempfile.TemporaryDirectory() as directory:
            os.chdir(directory)
            try:
                yield directory
            finally:
                os.chdir(original_directory)
