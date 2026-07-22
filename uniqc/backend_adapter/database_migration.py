"""Human-readable history for the task-cache schema.

The executable migration registry lives in
:mod:`uniqc.backend_adapter.task.store`; this module documents the intent of
each version for maintainers.

Schema version history
======================

Version 1: initial schema
-------------------------

Created the live ``tasks`` table and indices for backend, status, and
submission time. The table stores task identity, backend, status, shots,
timestamps, result JSON, and metadata JSON.

Version 2: archive support
--------------------------

Added ``archived_tasks`` so completed and failed tasks can leave the hot query
path while remaining recoverable. Gateway archive operations move rows between
the live and archived tables.

The migration creates the archive table and its indices::

    CREATE TABLE IF NOT EXISTS archived_tasks (
        task_id       TEXT PRIMARY KEY,
        backend       TEXT NOT NULL,
        status        TEXT NOT NULL,
        shots         INTEGER NOT NULL DEFAULT 0,
        submit_time   TEXT NOT NULL,
        update_time   TEXT NOT NULL,
        result_json   TEXT,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        archived_at   TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS archived_backend_idx
        ON archived_tasks(backend);
    CREATE INDEX IF NOT EXISTS archived_status_idx
        ON archived_tasks(status);
    CREATE INDEX IF NOT EXISTS archived_submit_time_idx
        ON archived_tasks(submit_time);

Future migration idea
=====================

An earlier design note proposed storing compiled-circuit JSON alongside the
submitted circuit. If revived, that change must be added to the canonical
registry in ``task/store.py`` and covered by migration tests before this
documentation is updated.
"""

# Current active schema version — must match CURRENT_SCHEMA_VERSION in store.py
CURRENT_SCHEMA_VERSION = 2
