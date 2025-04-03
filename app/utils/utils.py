from enum import Enum

class StringifiedEnum(Enum):
    """
    Custom Enum class that automatically converts enum members to their string representation.
    """
    def __str__(self):
        return str(self.value)
    
    def values(self):
        """
        Returns a list of all enum values.
        """
        return [member.value for member in self.__class__]
    
    def keys(self):
        """
        Returns a list of all enum keys.
        """
        return [member.name for member in self.__class__]
