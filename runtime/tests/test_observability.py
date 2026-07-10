"""Tests for observability module (structured logging + metrics)."""

from __future__ import annotations

import time

from runtime.observability import (
    Counter,
    Gauge,
    Histogram,
    MetricsRegistry,
    Timer,
    TimerContext,
)


class TestCounter:
    def test_init_zero(self):
        c = Counter()
        assert c.value == 0

    def test_inc(self):
        c = Counter()
        c.inc()
        assert c.value == 1

    def test_inc_multiple(self):
        c = Counter()
        c.inc(5)
        assert c.value == 5

    def test_thread_safety(self):
        import threading

        c = Counter()
        errors = []

        def bump():
            try:
                for _ in range(100):
                    c.inc()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=bump) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert c.value == 1000
        assert len(errors) == 0


class TestGauge:
    def test_init_zero(self):
        g = Gauge()
        assert g.value == 0.0

    def test_set(self):
        g = Gauge()
        g.set(42.5)
        assert g.value == 42.5

    def test_inc(self):
        g = Gauge()
        g.inc(5.0)
        assert g.value == 5.0

    def test_dec(self):
        g = Gauge()
        g.set(10.0)
        g.dec(3.0)
        assert g.value == 7.0


class TestHistogram:
    def test_empty_snapshot(self):
        h = Histogram()
        snap = h.snapshot()
        assert snap["count"] == 0

    def test_record(self):
        h = Histogram()
        h.observe(1.0)
        h.observe(2.0)
        h.observe(3.0)
        assert h.count == 3
        assert h.min == 1.0
        assert h.max == 3.0
        assert h.avg == 2.0

    def test_percentile(self):
        h = Histogram()
        for v in range(1, 101):
            h.observe(float(v))
        assert h.percentile(50) == 50.0
        assert h.percentile(95) == 95.0
        assert h.percentile(99) == 99.0
        assert h.percentile(0) == 1.0
        assert h.percentile(100) == 100.0

    def test_snapshot_contains_all_keys(self):
        h = Histogram()
        h.observe(5.0)
        snap = h.snapshot()
        for key in ("count", "sum", "min", "max", "avg", "p50", "p95", "p99"):
            assert key in snap


class TestTimer:
    def test_record(self):
        t = Timer()
        t.record_ms(150.0)
        snap = t.snapshot
        assert snap["count"] == 1
        assert snap["min"] == 150.0

    def test_record_seconds(self):
        t = Timer()
        t.record(0.5)
        snap = t.snapshot
        assert snap["count"] == 1
        assert snap["min"] == 0.5

    def test_multiple_records(self):
        t = Timer()
        t.record_ms(10.0)
        t.record_ms(20.0)
        t.record_ms(30.0)
        snap = t.snapshot
        assert snap["count"] == 3
        assert snap["p50"] == 20.0


class TestTimerContext:
    def test_records_duration(self):
        reg = MetricsRegistry()
        with TimerContext("test.duration", registry=reg):
            time.sleep(0.005)
        snap = reg.snapshot()
        key = "timer.test.duration"
        assert key in snap
        assert snap[key]["count"] == 1
        assert snap[key]["min"] >= 0.0


class TestMetricsRegistry:
    def test_counter(self):
        reg = MetricsRegistry()
        c = reg.counter("test.requests")
        c.inc()
        assert reg.counter("test.requests").value == 1

    def test_gauge(self):
        reg = MetricsRegistry()
        g = reg.gauge("test.sessions")
        g.set(5)
        assert reg.gauge("test.sessions").value == 5

    def test_histogram(self):
        reg = MetricsRegistry()
        h = reg.histogram("test.latency")
        h.observe(10.0)
        h.observe(20.0)
        snap = reg.snapshot()
        assert "histogram.test.latency" in snap
        assert snap["histogram.test.latency"]["count"] == 2

    def test_timer(self):
        reg = MetricsRegistry()
        t = reg.timer("test.op")
        t.record_ms(100.0)
        snap = reg.snapshot()
        assert "timer.test.op" in snap
        assert snap["timer.test.op"]["count"] == 1

    def test_summary(self):
        reg = MetricsRegistry()
        reg.counter("test.c").inc()
        summary = reg.summary()
        assert "test.c" in summary
        assert "Metrics Summary" in summary

    def test_thread_safety(self):
        import threading

        reg = MetricsRegistry()
        errors = []

        def record():
            try:
                for _ in range(100):
                    reg.counter("t.c").inc()
                    reg.timer("t.t").record_ms(1.0)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert reg.counter("t.c").value == 1000
        assert len(errors) == 0
