"""The supply chain day: locks hold, trust corroborates, the bill is whole.

Run with: python -m examples.supplychain
"""

from __future__ import annotations

from forge.cachetrust import TrustCache, register_trusted
from forge.lockfile import Available, Registry, install, resolve
from forge.sbom import BillOfMaterials, BomEntry


def locked_install():
    registry = Registry()
    registry.publish(Available("zlib", (1, 3), "zlib bytes"))
    registry.publish(Available("json", (2, 1), "json bytes"))
    manifest = {
        "zlib": ((1, 0), (2, 0)),
        "json": ((2, 0), (3, 0)),
    }
    lock = resolve(manifest, registry)
    registry.publish(Available("zlib", (1, 9), "midnight release"))
    installed = install(lock, registry)
    print(
        f"lockfile: installed zlib {lock['zlib'].version}, "
        f"the midnight 1.9 release changed nothing"
    )
    return installed


def shared_cache():
    cache = TrustCache()
    register_trusted(cache, "ci-fleet")
    cache.upload("compile:app", "digest-1", "laptop-9")
    first = cache.lookup("compile:app")
    cache.upload("compile:app", "digest-1", "laptop-3")
    second = cache.lookup("compile:app")
    print(
        f"trust:    quarantine served {first}, corroboration "
        f"served {second!r}"
    )
    print(f"          {cache.ledger()}")


def the_bill():
    bill = BillOfMaterials()
    bill.add(
        BomEntry(
            component="app",
            version="3.0",
            digest="aa" * 8,
            license_name="proprietary",
            origin="first-party",
        )
    )
    bill.add(
        BomEntry(
            component="zlib",
            version="1.3",
            digest="bb" * 8,
            license_name="Zlib",
            origin="external",
        )
    )
    bill.add(
        BomEntry(
            component="json",
            version="2.1",
            digest="cc" * 8,
            license_name="MIT",
            origin="external",
        )
    )
    page = bill.export({"app", "zlib", "json"})
    print(f"sbom:     {page.splitlines()[0]}")
    print(f"          licenses: {bill.license_summary()}")
    print(f"          externals: {', '.join(bill.externals())}")


def main() -> int:
    locked_install()
    shared_cache()
    the_bill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
