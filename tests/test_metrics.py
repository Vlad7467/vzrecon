from vzrecon.metrics import Meter, fmt_dur, fmt_int

def test_tick():
    m = Meter()
    m.tick(ok=True, latency_ms=10)
    m.tick(ok=False)
    m.tick(ok=True, latency_ms=20)
    assert m.done == 3
    assert m.ok == 2
    assert m.fail == 1

def test_p95():
    m = Meter()
    for v in range(100):
        m.tick(ok=True, latency_ms=float(v))
    assert m.percentile(0.5) == 50
    assert m.percentile(0.95) == 95

def test_progress():
    m = Meter()
    m.total = 10
    for _ in range(4):
        m.tick(ok=True)
    assert m.progress == 0.4

def test_fmt():
    assert fmt_int(1234567) == "1 234 567"
    assert fmt_dur(None) == "--:--"
    assert fmt_dur(65) == "01:05"
