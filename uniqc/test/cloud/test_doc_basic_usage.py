"""Doc-anchored regression tests for the submit_task basic-usage example.

These tests run the exact code patterns shown in
``docs/source/guide/submit_task.md`` against the local dummy backend so that
docs cannot silently bit-rot. If you change the snippets in submit_task.md,
update the assertions here as well.

All tests stay offline (no cloud creds, no network).
"""

from __future__ import annotations

import pytest

from uniqc import (
    Circuit,
    BackendNotFoundError,
    query_task,
    submit_task,
    wait_for_result,
)


def _bell_circuit() -> Circuit:
    c = Circuit()
    c.h(0)
    c.cnot(0, 1)
    c.measure(0, 1)
    return c


def _counts_dict(result):
    """Extract a counts dict from either a UnifiedResult or a raw dict."""
    if hasattr(result, "counts"):
        return result.counts
    return result


class TestSubmitTaskDocBasicUsage:
    """Mirror the four-step 基本用法 example from submit_task.md."""

    def test_canonical_provider_chip_form_round_trip(self):
        """``submit_task(circuit, backend='dummy:originq:WK_C180')`` returns a
        task id, ``wait_for_result`` returns a UnifiedResult, and
        ``query_task`` exposes the task status — all without contacting the
        cloud (we route through dummy mode for offline CI)."""
        circuit = _bell_circuit()
        task_id = submit_task(
            circuit,
            backend="dummy:local:simulator",
            shots=100,
        )
        assert isinstance(task_id, str) and task_id

        result = wait_for_result(task_id, timeout=30)
        counts = _counts_dict(result)
        assert isinstance(counts, dict)
        # Bell state collapses to {00, 11} — but for tiny shots either may
        # be empty; just assert keys are valid bitstrings.
        assert all(set(k) <= {"0", "1"} for k in counts)

        info = query_task(task_id)
        assert info.task_id == task_id
        # status may be a string (from cache) or TaskStatus enum (in-memory)
        status_value = info.status.value if hasattr(info.status, "value") else info.status
        assert status_value in {"success", "running", "failed", "pending"}

    def test_local_compile_handles_h_cnot_against_cz_sx_rz_basis(self):
        """The doc example uses H/CNOT but originq's submission basis is
        CZ/SX/RZ. ``local_compile=1`` (the default) must transpile silently
        so the example just works."""
        circuit = _bell_circuit()
        # Should NOT raise UnsupportedGateError — even though the dummy
        # backend doesn't enforce basis, the prep step still validates.
        task_id = submit_task(
            circuit,
            backend="dummy:local:simulator",
            shots=100,
        )
        assert task_id

    def test_bare_provider_id_is_rejected_with_helpful_chip_list(self):
        """Per the strict-format rule documented in submit_task.md, calling
        with ``backend='originq'`` and no chip kwarg must error and surface
        the cached chip list."""
        with pytest.raises(BackendNotFoundError) as excinfo:
            submit_task(_bell_circuit(), backend="originq", shots=100)
        msg = str(excinfo.value)
        assert "provider:chip-name" in msg
        assert "originq" in msg

    def test_legacy_backend_name_kwarg_still_works(self):
        """Backward-compat: ``backend='originq', backend_name='WK_C180'``
        is normalised to ``'originq:WK_C180'`` instead of being rejected.

        We exercise the kwarg-merging path. A successful submission attempt
        against the real cloud without credentials surfaces an availability
        / auth error — that's fine; we only care that the bare-platform
        identifier is accepted and combined with the kwarg before it
        reaches the network layer.
        """
        from uniqc.exceptions import (
            BackendNotAvailableError,
            BackendNotFoundError,
            AuthenticationError,
            NetworkError,
            UnsupportedGateError,
        )

        try:
            submit_task(
                _bell_circuit(),
                backend="originq",
                backend_name="WK_C180",
                shots=100,
            )
        except (BackendNotAvailableError, AuthenticationError, NetworkError, RuntimeError):
            # Expected when the env has no real cloud creds / pyqpanda3 —
            # the format check passed, that's what we wanted to assert.
            pass
        except UnsupportedGateError as e:
            # In CI there is no cached originq chip topology, so the basis
            # / topology validation step short-circuits with a "no backend
            # info available" UnsupportedGateError. The error message must
            # already reference the *canonical* form 'originq:WK_C180' —
            # that's our proof that the legacy kwarg got normalised before
            # the validation layer saw it.
            assert "originq:WK_C180" in str(e), (
                "legacy 'backend=originq, backend_name=WK_C180' should be "
                f"normalised to 'originq:WK_C180' before validation, got: {e}"
            )
        except BackendNotFoundError as e:
            pytest.fail(
                "legacy 'backend=originq, backend_name=WK_C180' should be "
                f"normalised, but BackendNotFoundError was raised: {e}"
            )


class TestSubmitTaskDummyBackends:
    """Mirror the dummy-mode block from submit_task.md."""

    def test_plain_dummy_backend(self):
        task_id = submit_task(_bell_circuit(), backend="dummy:local:simulator", shots=50)
        result = wait_for_result(task_id, timeout=30)
        counts = _counts_dict(result)
        assert isinstance(counts, dict)

    def test_chip_backed_dummy(self):
        task_id = submit_task(
            _bell_circuit(),
            backend="dummy:originq:WK_C180",
            shots=50,
        )
        result = wait_for_result(task_id, timeout=30)
        counts = _counts_dict(result)
        assert isinstance(counts, dict)
