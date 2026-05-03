"""Database migration documentation for uniqc.

This module records the history of schema versions applied to
``~/.uniqc/cache/tasks.sqlite``.  The canonical list lives in
``backend_adapter/task/store.py`` (:data:`MIGRATIONS`), but this file
serves as a human-readable changelog and a guide for future developers.

Schema version history
----------------------

v1 — Initial schema
    Created: 2026-05

    Tables
    ~~~~~~
    ``tasks``
        task_id       TEXT PRIMARY KEY
        backend       TEXT NOT NULL
        status        TEXT NOT NULL
        shots         INTEGER NOT NULL DEFAULT 0
        submit_time   TEXT NOT NULL
        update_time   TEXT NOT NULL
        result_json   TEXT
        metadata_json TEXT NOT NULL DEFAULT '{}'

    Indices
    ~~~~~~~
    tasks_backend_idx
    tasks_status_idx
    tasks_submit_time_idx


v2 — Archive support
    Created: 2026-05

    Motivation
    ~~~~~~~~~~
    Completed / failed tasks accumulate over time and slow down
    ``SELECT * FROM tasks ORDER BY submit_time DESC`` queries.
    Archiving moves them to a separate table that is not queried by
    default, keeping the hot path fast.

    Tables added
    ~~~~~~~~~~~~~
    ``archived_tasks``
        All columns of ``tasks`` plus:
        archived_at   TEXT NOT NULL  (ISO-8601 UTC timestamp)

    API impact
    ~~~~~~~~~~
    - GET /api/tasks  → queries ``tasks`` only (include_archived=False default)
    - GET /api/archive → queries ``archived_tasks``
    - POST /api/tasks/{id}/archive → moves row from ``tasks`` → ``archived_tasks``
    - POST /api/archive/restore/{id} → moves row back

    Migration SQL (automatically applied on DB open)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
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
    CREATE INDEX IF NOT EXISTS archived_backend_idx ON archived_tasks(backend);
    CREATE INDEX IF NOT EXISTS archived_status_idx  ON archived_tasks(status);
    CREATE INDEX IF NOT EXISTS archived_submit_time_idx ON archived_tasks(submit_time);


Future migrations (planned)
--------------------------

v3 — Compiled circuit storage (planned)
    Motivation
    ~~~~~~~~~~
    Store the compiled OriginIR / QASM circuit alongside the submitted
    circuit so that both "source" and "compiled" tabs in the circuit
    viewer always have data.

    Planned changes
    ~~~~~~~~~~~~~~
    ALTER TABLE tasks ADD COLUMN compiled_circuit_json TEXT;
    ALTER TABLE archived_tasks ADD COLUMN compiled_circuit_json TEXT;

    Notes
    ~~~~~
    - The JSON column stores the circuit in multiple formats
      (OriginIR, QASM, internal IR) keyed by format name.
    - Tooling in ``submit.py`` must be updated to populate this column
      at submission time.
"""

# Current active schema version — must match CURRENT_SCHEMA_VERSION in store.py
CURRENT_SCHEMA_VERSION = 2
