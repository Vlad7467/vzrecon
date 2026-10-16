# Architecture

## Concurrency model

Each `Scan` owns a bounded `asyncio.Queue` and a fixed pool of
worker coroutines. Workers pull until the queue is drained.

Why this shape:

- **vs. task-per-endpoint.** Fifty thousand `asyncio.Task`
  objects have measurable scheduler cost. The queue bounds live
  tasks by pool size regardless of list length.
- **vs. a global semaphore.** Semaphores serialize but do not
  bound pending coroutines. The queue bounds both memory and
  scheduler pressure.
- **vs. threads.** Proxies are I/O bound; threads add context
  switch cost without parallelism.

## Failure handling

Transport failures are counted, not logged. Scanning tens of
thousands of dead endpoints produces noise, not signal. Two
integers — `done`, `ok` — carry the information a log would.

Protocol failures and transport failures are indistinguishable
at the engine level: both are `None`.

## Output

Sinks open with `buffering=1`. On `SIGINT`, in-flight probes are
lost but every committed endpoint is on disk. Writes happen in
the worker, not a separate writer coroutine — a writer queue
would add a hop exactly where a hop is not affordable.

## Timing

`time.perf_counter` for latency — monotonic, unaffected by
wall-clock adjustments. Window starts at
`asyncio.open_connection` and ends when the protocol reply is
fully read, so the measurement covers TCP handshake plus protocol
round-trip.

## Self-test

`vzrecon --self-test` starts one mock server per protocol on
`127.0.0.1:0` and runs the corresponding validator against it.
Catches wire-format regressions, off-by-one in fixed reads,
error-classification drift. Does not catch network-level issues.
