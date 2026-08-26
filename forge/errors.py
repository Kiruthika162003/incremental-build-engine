"""Errors that name the mistake, because a build tool is a teacher.

Every refusal in this system says what was wrong and, where it can,
what would have been right, since the person reading it is holding
a broken build and the error message is the only documentation they
will consult. The hierarchy is shallow on purpose: callers catch
ForgeError when they want everything, or the specific class when
the recovery differs, and nothing here carries state beyond the
message and an optional detail map.
"""

from __future__ import annotations


class ForgeError(Exception):
    def __init__(self, message: str, **details):
        super().__init__(message)
        self.details = details


class Invalid(ForgeError):
    """The request contradicts itself; no build state was touched."""


class Missing(ForgeError):
    """Something referenced does not exist under that name."""


class Cycle(ForgeError):
    """The dependency graph loops, and the loop is in the message."""


class Hermetic(ForgeError):
    """An action touched something it never declared."""


class Stale(ForgeError):
    """A result was consulted after its inputs moved on."""
