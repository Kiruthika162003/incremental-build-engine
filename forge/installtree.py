"""The install tree: what ships is a contract, not whatever was lying around.

The build directory accumulates objects, logs, and intermediates,
and shipping it wholesale ships the mess. The install layout is a
declared mapping from built artifacts to their destinations, and
assembly enforces it in both directions: an artifact the build
never produced fails the install with the missing name, and the
strict sweep removes anything in the install root the layout does
not claim, because the file that ships by accident is the file
nobody patched. The layout digest folds destinations with content
so two installs compare as one string, and the drift check against
a previous digest names what moved, which is how a release manager
answers "is this the same package" without opening either one.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.content import digest_pairs
from forge.errors import Invalid, Missing
from forge.workspace import Workspace


@dataclass
class InstallLayout:
    mapping: dict[str, str] = field(default_factory=dict)

    def place(self, built: str, destination: str) -> None:
        if destination in self.mapping.values():
            raise Invalid(
                f"two artifacts claim {destination}; the package "
                f"cannot hold both"
            )
        if built in self.mapping:
            raise Invalid(f"{built} is already placed")
        self.mapping[built] = destination


@dataclass
class InstallReceipt:
    placed: list[str] = field(default_factory=list)
    swept: list[str] = field(default_factory=list)

    def line(self) -> str:
        return (
            f"{len(self.placed)} placed, {len(self.swept)} strays swept"
        )


def assemble(
    layout: InstallLayout,
    tree: Workspace,
    install_root: str = "dist",
) -> InstallReceipt:
    receipt = InstallReceipt()
    missing = [
        built
        for built in layout.mapping
        if not tree.exists(built)
    ]
    if missing:
        raise Missing(
            f"the build never produced {sorted(missing)}; "
            f"the install refuses to ship a hole"
        )
    claimed = set()
    for built, destination in sorted(layout.mapping.items()):
        target = f"{install_root}/{destination}"
        tree.write(target, tree.read(built))
        claimed.add(target)
        receipt.placed.append(target)
    for path in tree.under(install_root):
        if path not in claimed:
            tree.delete(path)
            receipt.swept.append(path)
    return receipt


def layout_digest(
    layout: InstallLayout, tree: Workspace, install_root: str = "dist"
) -> str:
    rows = []
    for destination in layout.mapping.values():
        target = f"{install_root}/{destination}"
        rows.append((destination, tree.digest_of(target)))
    return digest_pairs(rows)


def drift(
    previous: dict[str, str],
    layout: InstallLayout,
    tree: Workspace,
    install_root: str = "dist",
) -> list[str]:
    """Destinations whose content moved since the previous release."""
    moved = []
    for destination in sorted(layout.mapping.values()):
        target = f"{install_root}/{destination}"
        now = tree.digest_of(target)
        then = previous.get(destination)
        if then is None:
            moved.append(f"{destination}: new in this release")
        elif then != now:
            moved.append(f"{destination}: content moved")
    for destination in sorted(previous):
        if destination not in layout.mapping.values():
            moved.append(f"{destination}: dropped from the package")
    return moved
