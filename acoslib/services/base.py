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

