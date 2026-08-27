"""Trace stitching: one build, four services, and the log that went blind.

A developer's build touches the coordinator, a worker, the
cache, and the artifact store, and when it goes wrong the
evidence is four log files that do not know each other. The
trace id is the thread through them, and the stitcher's job is
reassembly: collect every span carrying the id, order them by
their declared start, and render the one timeline the incident
review actually wants. The diagnostic power is in the gaps:
a service that appears in the request path but contributed no
span is named blind, its logging broken exactly when it was
needed, and a span that starts before its parent's start is
named a clock skew witness, because two services disagreeing
about time is its own incident hiding inside this one. The
stitcher refuses to silently render a partial story as whole.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

REQUEST_PATH = ("coordinator", "worker", "cache", "store")


@dataclass(frozen=True)
class Span:
    trace_id: str
    service: str
    start: int
    ticks: int
    note: str


@dataclass
class TraceStitcher:
    spans: list[Span] = field(default_factory=list)

    def collect(self, span: Span) -> None:
        if span.ticks < 0:
            raise Invalid("a span cannot run negative ticks")
        self.spans.append(span)

    def timeline(self, trace_id: str) -> str:
        mine = sorted(
            (
                span
                for span in self.spans
                if span.trace_id == trace_id
            ),
            key=lambda span: (span.start, span.service),
        )
        if not mine:
            raise Invalid(
                f"{trace_id} left no spans anywhere; either the "
                "id is wrong or everything is blind"
            )
        lines = []
        for span in mine:
            lines.append(
                f"  [{span.start:>4}] {span.service}: "
                f"{span.note} ({span.ticks} ticks)"
            )
        blind = [
            service
            for service in REQUEST_PATH
            if not any(
                span.service == service for span in mine
            )
        ]
        anchor = next(
            (
                span
                for span in mine
                if span.service == "coordinator"
            ),
            None,
        )
        skewed = (
            [
                f"{span.service} starts at {span.start} before "
                f"the coordinator's {anchor.start}"
                for span in mine
                if anchor is not None
                and span.service != "coordinator"
                and span.start < anchor.start
            ]
            if anchor is not None
            else []
        )
        header = (
            f"{trace_id}: {len(mine)} span(s) across "
            f"{len(set(s.service for s in mine))} service(s)"
        )
        if blind:
            lines.append(
                f"  BLIND: {', '.join(blind)} contributed no "
                "span; their logging broke exactly when it was "
                "needed"
            )
        for witness in skewed:
            lines.append(
                f"  CLOCK SKEW: {witness}; two services "
                "disagreeing about time is its own incident"
            )
        if blind:
            header += " (partial, and saying so)"
        return "\n".join([header, *lines])
