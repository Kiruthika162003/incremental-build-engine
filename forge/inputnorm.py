"""Input normalization: one file must not have two digests on two machines.

The oldest cross-platform cache killer is the checkout itself:
the same source file arrives with LF on one machine and CRLF on
another, the digests disagree, and the farm's cache splits into
a Windows half and a Linux half that never share a byte. The
normalizer digests text through a canonical form, line endings
unified, a final newline ensured, BOM stripped, so the digest
answers "same meaning" instead of "same bytes". Binary files are
the opposite contract, digested raw, because normalizing a PNG
corrupts it, and the classifier that tells the two apart refuses
to guess on evidence of both: a file with text extension and NUL
bytes is named as a lie, not silently hashed either way, since
misclassification in either direction poisons the cache quietly.
"""

from __future__ import annotations

from forge.content import digest_bytes
from forge.errors import Invalid

TEXT_SUFFIXES = (".c", ".h", ".py", ".txt", ".md", ".build", ".json")
BOM = b"\xef\xbb\xbf"


def looks_binary(payload: bytes) -> bool:
    return b"\x00" in payload


def is_text_path(path: str) -> bool:
    return path.endswith(TEXT_SUFFIXES)


def canonical_text(payload: bytes) -> bytes:
    body = payload.removeprefix(BOM)
    body = body.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    if body and not body.endswith(b"\n"):
        body += b"\n"
    return body


def normalized_digest(path: str, payload: bytes) -> str:
    text_by_name = is_text_path(path)
    binary_by_content = looks_binary(payload)
    if text_by_name and binary_by_content:
        raise Invalid(
            f"{path} claims to be text but contains NUL bytes; "
            "hashing a lie either way poisons the cache quietly"
        )
    if text_by_name:
        return digest_bytes(canonical_text(payload))
    return digest_bytes(payload)


def platform_agreement(
    path: str, checkouts: dict[str, bytes]
) -> str:
    if len(checkouts) < 2:
        raise Invalid(
            "agreement needs at least two checkouts to compare"
        )
    digests = {
        machine: normalized_digest(path, payload)
        for machine, payload in checkouts.items()
    }
    distinct = sorted(set(digests.values()))
    if len(distinct) == 1:
        return (
            f"{path}: {len(checkouts)} checkout(s) agree on "
            f"{distinct[0][:8]}"
        )
    lines = [
        f"{path}: the checkouts disagree even after "
        "normalization; this is content drift, not line endings"
    ]
    for machine in sorted(digests):
        lines.append(f"  {machine}: {digests[machine][:8]}")
    return "\n".join(lines)


def raw_split_cost(
    path: str, checkouts: dict[str, bytes]
) -> str:
    raw = {digest_bytes(payload) for payload in checkouts.values()}
    normalized = {
        normalized_digest(path, payload)
        for payload in checkouts.values()
    }
    healed = len(raw) - len(normalized)
    return (
        f"{path}: raw digests split the cache {len(raw)} way(s), "
        f"normalization heals {healed} split(s)"
    )
