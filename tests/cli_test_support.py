"""Test-only Click runner compatibility helpers."""

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext

from click.testing import CliRunner as ClickCliRunner


class CliRunner(ClickCliRunner):
    """Keep CLI tests isolated without Click's deprecated helper."""

    @contextmanager
    def isolated_filesystem(
        self,
        temp_dir: str | os.PathLike[str] | None = None,
    ) -> Iterator[str]:
        original_directory = os.getcwd()
        directory_context = (
            tempfile.TemporaryDirectory()
            if temp_dir is None
            else nullcontext(tempfile.mkdtemp(dir=temp_dir))
        )
        with directory_context as directory:
            os.chdir(directory)
            try:
                yield directory
            finally:
                os.chdir(original_directory)
