# incremental-build-engine

An incremental build system that treats content as identity and
honesty as a feature. The package is called `forge`. Actions are
keyed by what they read, what they run, and what they write;
builds stop early when outputs come back byte-identical; and
every optimization in the repository carries a ledger that says
what it actually saved, because a build system that cannot
explain itself gets replaced by superstition.

## The shape of the repository

- `forge/` holds about a hundred modules. The core is small:
  a content-addressed store, a dependency graph that refuses
  cycles at declaration, a workspace that meters every read and
  write, actions with observed-versus-declared hermeticity, an
  action cache that never stores dirty results, and an engine
  whose early cutoff turns byte-identical rebuilds into rows of
  cache hits. Everything else is the operational world those
  cores live in: remote caches and their economics, flakiness
  certification, sandboxes, version stamps, test selection,
  merge queues, release trains, promotion ladders, spot
  instance arithmetic, thermal scheduling, error budgets, game
  days, and the rest.
- `forge/audits/` is the repository's signature voice: 21
  audits, each a measured drill whose docstring records what
  was claimed, what was measured, and where the first guess
  was wrong. The registry runs them all; `forge summary`
  prints one line, currently `21 audits (0 broken)`, and the
  final audit, `gatecheck`, feeds the live registry into the
  ship gate, the audit that audits the auditors.
- `examples/` holds 19 worked days and weeks, from a first
  project's cold build to migration day, the cache's day, the
  night shift, the incident review, and ship day. Every
  example's printed output is asserted line by line in the
  test suite.
- `tests/` holds 1,744 tests, one file per module, all green.

## The house rules the code was written under

- Measurements outrank prose. When a guess was refuted by a
  test run, the wrong guess stays recorded in the docstring
  beside the measured truth. The repository keeps its
  corrections: the remote cache that charged two round trips
  where one was promised, the worker curve with two cliffs
  instead of a slope, the delta-debugging price list rewritten
  by its own meter, the bloom filter that under-delivers its
  dial on small fleets, the nines label that was wrong twice
  at the same boundary.
- Refusals carry sentences, not codes. A cycle names its loop,
  a torn world names both revisions, a fenced write names the
  token gap, and a no-go names its blocker, because the error
  message is the interface most users meet first.
- Ledgers price both directions. Idle ticks and queued ticks,
  hoarding and thrashing, freight saved and freight wasted:
  a number that only justifies is advertising.

## Running it

```
python -m pytest tests/ -q
python -m forge.cli summary
python -m forge.cli audits
python -m examples.firstproject
```

Python 3.11 or later, no dependencies outside the standard
library. Linted with ruff, line length 96.

## Numbers at close

30,020 strict lines of Python (excluding docstrings, comments,
and blank lines), 1,744 tests, 21 audits with zero broken,
19 tested examples, 258 commits.

Written by Kiruthika Subramani in collaboration with Claude, Anthropic's AI assistant.
