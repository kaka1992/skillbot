from jupyter.cell_execution import (
    CellExecutionReceipt,
    CellRequestState,
    CellSpec,
    ExecutionCoordinator,
    ReceiptPhase,
)


def _receipt(request, phase, **kwargs):
    return CellExecutionReceipt(
        request_id=request.request_id,
        batch_id=request.batch_id,
        notebook_path=request.notebook_path,
        kernel_id=request.kernel_id,
        phase=phase,
        timestamp_ms=1,
        **kwargs,
    )


def test_serial_batch_dispatches_next_only_after_success():
    sent = []
    events = []
    callbacks = {}

    def sender(request, callback):
        sent.append(request)
        callbacks[request.request_id] = callback

    coordinator = ExecutionCoordinator(
        sender,
        lambda event, item, batch, receipt: events.append(event),
        materialize_timeout_ms=10_000,
    )
    batch = coordinator.submit_batch(
        [CellSpec("a = 1"), CellSpec("b = a + 1")],
        "demo.ipynb",
        "kernel-1",
        auto_execute=True,
    )

    assert len(sent) == 1
    first = sent[0]
    callbacks[first.request_id](_receipt(first, ReceiptPhase.MATERIALIZED, cell_id="a"))
    callbacks[first.request_id](_receipt(first, ReceiptPhase.STARTED, cell_id="a"))
    callbacks[first.request_id](_receipt(first, ReceiptPhase.SUCCEEDED, cell_id="a"))

    assert len(sent) == 2
    second = sent[1]
    callbacks[second.request_id](_receipt(second, ReceiptPhase.MATERIALIZED, cell_id="b"))
    callbacks[second.request_id](_receipt(second, ReceiptPhase.STARTED, cell_id="b"))
    callbacks[second.request_id](_receipt(second, ReceiptPhase.SUCCEEDED, cell_id="b"))

    assert batch.is_terminal
    assert batch.is_success
    assert events.count("batch_succeeded") == 1
    assert coordinator._batches == {}
    assert coordinator._requests == {}


def test_failure_cancels_remaining_requests():
    sent = []
    callbacks = {}
    events = []

    def sender(request, callback):
        sent.append(request)
        callbacks[request.request_id] = callback

    coordinator = ExecutionCoordinator(
        sender,
        lambda event, item, batch, receipt: events.append(event),
        materialize_timeout_ms=10_000,
    )
    batch = coordinator.submit_batch(
        [CellSpec("raise ValueError()"), CellSpec("never = True")],
        "demo.ipynb",
        "kernel-1",
        auto_execute=True,
    )
    request = sent[0]
    callbacks[request.request_id](
        _receipt(request, ReceiptPhase.MATERIALIZED, cell_id="a")
    )
    callbacks[request.request_id](_receipt(request, ReceiptPhase.STARTED, cell_id="a"))
    callbacks[request.request_id](
        _receipt(
            request,
            ReceiptPhase.FAILED,
            cell_id="a",
            error_code="CELL_EXECUTION_ERROR",
        )
    )

    assert len(sent) == 1
    assert batch.requests[0].state is CellRequestState.FAILED
    assert batch.requests[1].state is CellRequestState.CANCELLED
    assert batch.is_terminal
    assert "batch_failed" in events


def test_non_auto_batch_completes_on_materialized():
    sent = []
    callbacks = {}

    def sender(request, callback):
        sent.append(request)
        callbacks[request.request_id] = callback

    coordinator = ExecutionCoordinator(
        sender,
        lambda *args: None,
        materialize_timeout_ms=10_000,
    )
    batch = coordinator.submit_batch(
        [CellSpec("a = 1"), CellSpec("b = 2")],
        "demo.ipynb",
        "kernel-1",
        auto_execute=False,
    )
    first = sent[0]
    callbacks[first.request_id](_receipt(first, ReceiptPhase.MATERIALIZED, cell_id="a"))
    second = sent[1]
    callbacks[second.request_id](_receipt(second, ReceiptPhase.MATERIALIZED, cell_id="b"))

    assert batch.is_success


def test_duplicate_receipt_is_idempotent():
    events = []
    sent = []
    callbacks = {}

    def sender(request, callback):
        sent.append(request)
        callbacks[request.request_id] = callback

    coordinator = ExecutionCoordinator(
        sender,
        lambda event, *args: events.append(event),
        materialize_timeout_ms=10_000,
    )
    coordinator.submit_batch(
        [CellSpec("a = 1")],
        "demo.ipynb",
        "kernel-1",
        auto_execute=True,
    )
    request = sent[0]
    receipt = _receipt(request, ReceiptPhase.MATERIALIZED, cell_id="a")
    callbacks[request.request_id](receipt)
    callbacks[request.request_id](receipt)

    assert events.count("materialized") == 1


def test_out_of_order_terminal_receipt_is_ignored():
    sent = []
    callbacks = {}
    events = []

    def sender(request, callback):
        sent.append(request)
        callbacks[request.request_id] = callback

    coordinator = ExecutionCoordinator(
        sender,
        lambda event, *args: events.append(event),
        materialize_timeout_ms=10_000,
    )
    batch = coordinator.submit_batch(
        [CellSpec("a = 1")],
        "demo.ipynb",
        "kernel-1",
        auto_execute=True,
    )
    request = sent[0]
    callbacks[request.request_id](_receipt(request, ReceiptPhase.SUCCEEDED))

    assert batch.requests[0].state is CellRequestState.SENT
    assert "succeeded" not in events


def test_cancel_closes_non_terminal_request():
    sent = []
    closed = []

    def sender(request, callback):
        sent.append(request)

    coordinator = ExecutionCoordinator(
        sender,
        lambda *args: None,
        materialize_timeout_ms=10_000,
        close_request=closed.append,
    )
    batch = coordinator.submit_batch(
        [CellSpec("a = 1")],
        "demo.ipynb",
        "kernel-1",
        auto_execute=True,
    )
    coordinator.cancel_active()

    assert batch.requests[0].state is CellRequestState.CANCELLED
    assert closed == [sent[0].request_id]


def test_sender_error_becomes_rejected_batch():
    events = []

    def sender(request, callback):
        raise RuntimeError("extension unavailable")

    coordinator = ExecutionCoordinator(
        sender,
        lambda event, *args: events.append(event),
        materialize_timeout_ms=10_000,
    )
    batch = coordinator.submit_batch(
        [CellSpec("a = 1")],
        "demo.ipynb",
        "kernel-1",
        auto_execute=True,
    )

    assert batch.requests[0].state is CellRequestState.REJECTED
    assert batch.is_terminal
    assert "rejected" in events
    assert "batch_failed" in events


def test_timeout_side_effects_use_configured_scheduler():
    scheduled = []
    closed = []
    events = []

    coordinator = ExecutionCoordinator(
        lambda *args: None,
        lambda event, *args: events.append(event),
        materialize_timeout_ms=10_000,
        close_request=closed.append,
        schedule=scheduled.append,
    )
    batch = coordinator.submit_batch(
        [CellSpec("a = 1")],
        "demo.ipynb",
        "kernel-1",
        auto_execute=True,
    )
    item = batch.requests[0]
    coordinator._cancel_timer(item)

    coordinator._schedule_timeout(
        item.request.request_id,
        "MATERIALIZE_TIMEOUT",
        item.timer_generation,
    )

    assert item.state is CellRequestState.SENT
    assert len(scheduled) == 1

    scheduled[0]()

    assert item.state is CellRequestState.TIMED_OUT
    assert closed == [item.request.request_id]
    assert "timed_out" in events


def test_materialized_replaces_short_timeout_with_execution_timeout():
    sent = []
    callbacks = {}

    def sender(request, callback):
        sent.append(request)
        callbacks[request.request_id] = callback

    coordinator = ExecutionCoordinator(
        sender,
        lambda *args: None,
        materialize_timeout_ms=10_000,
    )
    batch = coordinator.submit_batch(
        [CellSpec("a = 1")],
        "demo.ipynb",
        "kernel-1",
        auto_execute=True,
        timeout_ms=20_000,
    )
    item = batch.requests[0]
    materialize_timer = item.timer

    callbacks[item.request.request_id](
        _receipt(item.request, ReceiptPhase.MATERIALIZED, cell_id="a")
    )

    assert item.timer is not materialize_timer
    assert materialize_timer.finished.is_set()
    materialized_generation = item.timer_generation

    coordinator._timeout_request(
        item.request.request_id,
        "MATERIALIZE_TIMEOUT",
    )

    assert item.state is CellRequestState.MATERIALIZED

    callbacks[item.request.request_id](
        _receipt(item.request, ReceiptPhase.STARTED, cell_id="a")
    )
    coordinator._timeout_request(
        item.request.request_id,
        "EXECUTION_TIMEOUT",
        materialized_generation,
    )

    assert item.state is CellRequestState.STARTED
    coordinator.cancel_active()
