from enum import Enum


class StringifiedEnum(Enum):
    def __str__(self):
        return str(self.value)

    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        return super().__eq__(other)

    def __ne__(self, other):
        if isinstance(other, str):
            return self.value != other
        return super().__ne__(other)

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        return f"{self.__class__.__name__}.{self.name}"

    def values(self):
        return [member.value for member in self.__class__]

    def keys(self):
        return [member.name for member in self.__class__]
