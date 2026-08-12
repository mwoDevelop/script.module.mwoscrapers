from mwoscrapers import health


def test_failures_quarantine_only_the_failing_provider(monkeypatch):
    clock = [10.0]
    monkeypatch.setattr(health, "monotonic", lambda: clock[0])
    health._STATE.clear()

    for _ in range(3):
        health.failure("broken", threshold=3, quarantine_seconds=30)

    assert health.available("broken") is False
    assert health.available("healthy") is True

    clock[0] = 41.0
    assert health.available("broken") is True
    health.success("broken")
    assert health._STATE["broken"].failures == 0
