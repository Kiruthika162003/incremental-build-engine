"""Container layers: each one a cache entry, the volatile one last.

An image is a stack of layers and the cache rule is brutal: a
changed layer invalidates itself and everything above it, so the
order of the stack is the shape of the bill. The builder digests
each layer from its content plus every layer beneath, which is
exactly the invalidation the runtime enforces, and the stack
report prices a change at each position so the classic mistake,
COPY source before RUN install, is a number instead of a code
review comment: sources change daily and dependencies monthly,
and a stack that puts the daily thing under the monthly thing
rebuilds the monthly thing daily. The advisor sorts layers by
measured change frequency and reports the stack's cost against
the optimal order's, since the argument for reordering a
Dockerfile is always the difference between two bills.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.content import digest_text
from forge.errors import Invalid


@dataclass(frozen=True)
class Layer:
    name: str
    content: str
    build_cost: int


@dataclass
class ImageBuilder:
    cache: dict[str, str] = field(default_factory=dict)
    rebuilds: int = 0
    layer_hits: int = 0

    def build(self, stack: list[Layer]) -> list[str]:
        if not stack:
            raise Invalid("an image needs at least one layer")
        digests = []
        below = ""
        for layer in stack:
            digest = digest_text(f"{below}|{layer.content}")
            if self.cache.get(layer.name) == digest:
                self.layer_hits += 1
            else:
                self.cache[layer.name] = digest
                self.rebuilds += 1
            digests.append(digest)
            below = digest
        return digests


def change_bill(stack: list[Layer], changed_index: int) -> int:
    """Ticks paid when the layer at this index changes."""
    if not 0 <= changed_index < len(stack):
        raise Invalid("no such layer")
    return sum(
        layer.build_cost for layer in stack[changed_index:]
    )


def expected_bill(
    stack: list[Layer], change_frequency: dict[str, int]
) -> int:
    """Total ticks per period given each layer's changes per period."""
    total = 0
    for index, layer in enumerate(stack):
        changes = change_frequency.get(layer.name, 0)
        total += changes * change_bill(stack, index)
    return total


def advise(
    stack: list[Layer], change_frequency: dict[str, int]
) -> str:
    current = expected_bill(stack, change_frequency)
    optimal_stack = sorted(
        stack,
        key=lambda layer: (
            change_frequency.get(layer.name, 0),
            layer.name,
        ),
    )
    optimal = expected_bill(optimal_stack, change_frequency)
    if current == optimal:
        return (
            f"the stack is optimal at {current} ticks per period; "
            f"volatile layers already sit on top"
        )
    order = " -> ".join(layer.name for layer in optimal_stack)
    return (
        f"reorder to [{order}]: {current} ticks per period becomes "
        f"{optimal}, a saving of {current - optimal}"
    )
