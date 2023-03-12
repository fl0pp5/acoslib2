from __future__ import annotations

import typing

from acoslib import types


class BaseService:
    __slots__ = (
        "_reference",
    )

    def __init__(self, reference: types.Reference) -> None:
        self._reference = reference

    @property
    def reference(self) -> types.Reference:
        return self._reference

    def to(self, service_t: typing.Type[BaseService], reference: types.Reference = None) -> BaseService:
        return service_t(reference or self._reference)
