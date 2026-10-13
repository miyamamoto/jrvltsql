"""Test-side helpers for driving :class:`DataImporter`.

`DataImporter.import_single_record` used to be a second implementation of the
batch path, kept alive only by these tests. It is gone; `import_records` is the
single entry point. `import_one` keeps the one thing the tests actually wanted
from it - "import exactly this record and tell me whether it landed".

`import_single_record` returned True whenever it handled the record without
counting a failure, including paths that deliberately added nothing to
`records_imported` such as a physical erase. `import_one` keeps that contract by
reading the failure count of the call itself.

Note that `import_records` resets its counters on entry (`importer.py`: "Every
call owns a fresh statistics interval"), so the returned dictionary describes
that one call and `get_statistics()` afterwards describes the last call only -
not the run. Tests that need a total across calls have to add it up themselves.
"""

from src.importer.importer import DataImporter


def import_one(importer: DataImporter, record: dict, **kwargs) -> bool:
    """Import a single record through `import_records`.

    Returns True when the call reported no failure, mirroring the boolean the
    removed `import_single_record` returned.
    """
    return importer.import_records(iter([record]), **kwargs)["records_failed"] == 0


def import_each(importer: DataImporter, records, **kwargs) -> dict:
    """Import records one at a time and return the totals for the whole run.

    The removed `import_single_record` accumulated its statistics across calls,
    so a test could read a run total off `get_statistics()`. `import_records`
    resets on entry, so the total has to be added up here.
    """
    totals = {"records_imported": 0, "records_failed": 0, "batches_processed": 0}
    for record in records:
        stats = importer.import_records(iter([record]), **kwargs)
        for key in totals:
            totals[key] += stats[key]
    return totals
