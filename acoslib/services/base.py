from __future__ import annotations

from acoslib import types


class AltcosService:
    __slots__ = (
        "_reference",
    )

    def __init__(self, reference: types.Reference, **extra) -> None:
        self._reference = reference

    @property
    def reference(self) -> types.Reference:
        return self._reference

