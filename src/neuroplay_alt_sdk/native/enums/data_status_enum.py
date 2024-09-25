from enum import Enum, auto


class DataStatusEnum(Enum):
    VALID = auto()
    WARN = auto()
    NOT_VALID = auto()
