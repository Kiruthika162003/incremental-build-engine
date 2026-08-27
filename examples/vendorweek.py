"""A week of vendoring: the mirror, the patches, the lawyers, the blame.

Run with: python -m examples.vendorweek
"""

from __future__ import annotations

from forge.fetchplan import FetchPlan, Pin
from forge.licensecheck import (
    NOTICE,
    PERMISSIVE,
    License,
    LicenseGraph,
)
from forge.patchqueue import Patch, PatchQueue
from forge.whyrebuild import ActionShot, RebuildExplainer

UPSTREAM_1_3 = "int inflate(z_stream *s) {\n  fast_path(s);\n}\n"
UPSTREAM_1_4 = "int inflate(z_stream *s) {\n  faster_path(s);\n}\n"


def monday_the_mirror():
    plan = FetchPlan()
    plan.add(Pin(name="zlib", version="1.3", digest="aabbccdd0011"))
    plan.add(Pin(name="curl", version="8.5", digest="deadbeef4455"))
    mirror = {
        "mirror/zlib/aabbccdd/zlib-1.3.tar": "aabbccdd0011",
        "mirror/curl/deadbeef/curl-8.5.tar": "0000000099aa",
        "mirror/old/leftover.tar": "11",
    }
    print(f"monday:   {plan.verdict(mirror).splitlines()[1].strip()}")
    mirror["mirror/curl/deadbeef/curl-8.5.tar"] = "deadbeef4455"
    print(f"          refetched: {plan.verdict(mirror)}")


def tuesday_the_patches():
    queue = PatchQueue()
    queue.add(
        Patch.against(
            UPSTREAM_1_3,
            "win32-workaround",
            "fast_path(s);",
            "fast_path(s); flush_win32(s);",
        )
    )
    patched = queue.apply(UPSTREAM_1_3)
    print(
        f"tuesday:  patch landed, flush call present: "
        f"{'flush_win32' in patched}"
    )
    stale = queue.stale_against(UPSTREAM_1_4)
    print(
        f"          zlib 1.4 arrives: stale = {stale}, "
        "rebase before building"
    )


def wednesday_the_lawyers():
    graph = LicenseGraph()
    graph.declare(
        "zlib",
        License(
            name="Zlib-ack",
            kind=NOTICE,
            attribution="Compression by the zlib authors.",
        ),
    )
    graph.declare("curl", License(name="MIT", kind=PERMISSIVE))
    graph.declare(
        "app",
        License(name="MIT", kind=PERMISSIVE),
        needs=("zlib", "curl"),
    )
    print(
        f"wednesday: {graph.verdict('app', (PERMISSIVE, NOTICE))}"
    )
    print(f"          NOTICE: {graph.notice_file('app')}")


def thursday_the_blame():
    explainer = RebuildExplainer()

    def build(zlib_digest, app_digest):
        return {
            "vendor": ActionShot(
                command="unpack zlib.tar",
                inputs=(("zlib.tar", zlib_digest),),
                outputs=("zlib.c",),
            ),
            "compile": ActionShot(
                command="cc zlib.c",
                inputs=(("zlib.c", app_digest),),
                outputs=("zlib.o",),
            ),
        }

    explainer.record(build("tar-13", "src-13"))
    explainer.record(build("tar-14", "src-14"))
    print("thursday: " + explainer.explain("compile").splitlines()[0])
    print(
        f"          root causes: "
        f"{explainer.root_causes('compile')}"
    )


def main() -> int:
    monday_the_mirror()
    tuesday_the_patches()
    wednesday_the_lawyers()
    thursday_the_blame()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
