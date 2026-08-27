"""Multi-tenancy: the cache knows you both built the same LLVM.

Two organizations on one farm pose a question nobody prices
until legal does: content-addressed storage deduplicates
identical bytes, so if tenant B compiles the same LLVM tarball
tenant A compiled yesterday, a shared CAS serves it instantly,
and in doing so confirms to B that somebody else built exactly
these bytes, which is an existence leak, small but real. The
model offers the three honest policies: shared, maximum dedup
and the leak accepted in writing; private, full isolation with
every common dependency built twice and stored twice; and
salted, private namespaces that rejoin for allowlisted public
sources, which captures most of the dedup while confining the
leak to bytes both tenants already agree are public. The
report prices all three on the same workload, because this is
a decision for a signature, not a default, and the signature
deserves numbers.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid


@dataclass(frozen=True)
class Workload:
    common_public_units: int
    common_private_units: int
    unique_units_per_tenant: int
    ticks_per_unit: int
    tenants: int = 2

    def __post_init__(self) -> None:
        if self.tenants < 2:
            raise Invalid("one tenant is not tenancy")
        if self.ticks_per_unit <= 0:
            raise Invalid("units need positive cost")


def price_shared(load: Workload) -> tuple[int, str]:
    builds = (
        load.common_public_units
        + load.common_private_units
        + load.unique_units_per_tenant * load.tenants
    )
    return builds * load.ticks_per_unit, (
        "existence leak accepted in writing: dedup confirms "
        "a co-tenant built the same bytes"
    )


def price_private(load: Workload) -> tuple[int, str]:
    builds = (
        load.common_public_units
        + load.common_private_units
        + load.unique_units_per_tenant
    ) * load.tenants
    return builds * load.ticks_per_unit, (
        "full isolation: every common dependency built and "
        "stored once per tenant"
    )


def price_salted(load: Workload) -> tuple[int, str]:
    builds = (
        load.common_public_units
        + load.common_private_units * load.tenants
        + load.unique_units_per_tenant * load.tenants
    )
    return builds * load.ticks_per_unit, (
        "private namespaces rejoining for allowlisted public "
        "sources: the leak is confined to bytes both already "
        "agree are public"
    )


def signature_page(load: Workload) -> str:
    shared, shared_note = price_shared(load)
    private, private_note = price_private(load)
    salted, salted_note = price_salted(load)
    lines = [
        "a decision for a signature, not a default:",
        f"  shared: {shared} tick(s); {shared_note}",
        f"  salted: {salted} tick(s); {salted_note}",
        f"  private: {private} tick(s); {private_note}",
        (
            f"  isolation premium: {private - shared} tick(s); "
            f"the salted compromise recovers "
            f"{private - salted} of it"
        ),
    ]
    return "\n".join(lines)
