"""Packing artifacts onto volumes: sorted greed saves real disks.

Artifacts land on storage volumes with hard capacities, and the
naive placer, first volume with room in arrival order, wastes
space at every seam because big artifacts arrive after small
ones have salted every volume with crumbs. First-fit-decreasing
sorts before placing, big rocks first, and the difference is
not style: on the same artifact set it routinely closes a whole
volume the naive order leaves open, which at fleet scale is a
purchase order. The packer refuses an artifact larger than any
volume outright with the only honest advice, split it or buy
bigger disks, and the comparison report prints both packings
side by side, since "sort first" is advice nobody takes from a
sentence and everybody takes from a bill.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid


@dataclass
class Packing:
    volume_size: int
    volumes: list[list[int]]

    def volume_count(self) -> int:
        return len(self.volumes)

    def waste(self) -> int:
        return sum(
            self.volume_size - sum(held)
            for held in self.volumes
        )


def _place(
    sizes: list[int], volume_size: int
) -> Packing:
    for size in sizes:
        if size > volume_size:
            raise Invalid(
                f"an artifact of {size} exceeds the volume "
                f"size {volume_size}; split it or buy bigger "
                "disks"
            )
        if size <= 0:
            raise Invalid("artifacts need positive sizes")
    volumes: list[list[int]] = []
    for size in sizes:
        for held in volumes:
            if sum(held) + size <= volume_size:
                held.append(size)
                break
        else:
            volumes.append([size])
    return Packing(volume_size=volume_size, volumes=volumes)


def naive_pack(sizes: list[int], volume_size: int) -> Packing:
    if not sizes:
        raise Invalid("nothing to pack")
    return _place(list(sizes), volume_size)


def sorted_pack(sizes: list[int], volume_size: int) -> Packing:
    if not sizes:
        raise Invalid("nothing to pack")
    return _place(sorted(sizes, reverse=True), volume_size)


def comparison_bill(
    sizes: list[int], volume_size: int
) -> str:
    naive = naive_pack(sizes, volume_size)
    clever = sorted_pack(sizes, volume_size)
    saved = naive.volume_count() - clever.volume_count()
    line = (
        f"arrival order uses {naive.volume_count()} volume(s) "
        f"wasting {naive.waste()}; sorted greed uses "
        f"{clever.volume_count()} wasting {clever.waste()}"
    )
    if saved > 0:
        line += (
            f"; sorting closed {saved} whole volume(s), which "
            "at fleet scale is a purchase order"
        )
    else:
        line += "; this artifact set forgives the naive order"
    return line
