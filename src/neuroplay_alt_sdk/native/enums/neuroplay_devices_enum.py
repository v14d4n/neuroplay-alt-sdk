from enum import Enum


class NeuroPlayDevicesEnum(Enum):
    ALL = "NeuroPlay"
    NEUROPLAY_6C = "NeuroPlay-6C"
    NEUROPLAY_8CAP = "NeuroPlay-8Cap"
    __UNDEFINED = ""

    @classmethod
    def from_string(cls, device_name: str) -> 'NeuroPlayDevicesEnum':
        for device in NeuroPlayDevicesEnum:
            if device.value == device_name:
                return device
        return cls.__UNDEFINED
