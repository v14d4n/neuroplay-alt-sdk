import asyncio
import logging
import re
from typing import AsyncGenerator, List, Optional, Dict, Set, Type, TypeVar

from bleak import BleakScanner
from bleak.backends.device import BLEDevice

from ..enums import NeuroPlayDevicesEnum
from ..devices import AbstractNeuroPlayDevice, NeuroPlayDevice

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=AbstractNeuroPlayDevice)


class NeuroPlayScanner(AsyncGenerator[T, None]):
    """
    Example usage:

    async with NeuroPlayScanner() as scanner:
        async for device in scanner:
            do your job with device here
    """

    def __init__(self,
                 device_class: Type[T] = NeuroPlayDevice,
                 devices_names: Set[NeuroPlayDevicesEnum] = (
                         NeuroPlayDevicesEnum.ALL,
                 ),
                 timeout: int = 5) -> None:
        """
        :param devices_names:
        :param timeout:
        :raises ValueError: The set 'devices_names' should not be empty.
        """
        if not devices_names:
            raise ValueError("The set 'devices_names' should not be empty.")

        self.__timeout = timeout
        self.__devices_names = devices_names
        self.__discovered_devices: Dict[str, T] = {}
        self.__scanner: BleakScanner = BleakScanner()
        self.__generator: AsyncGenerator[BLEDevice, None] = self.__discover_generator()
        self.__device_class = device_class

    async def __aenter__(self) -> 'NeuroPlayScanner':
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()
        self.clear_discovered_devices()

    def __aiter__(self) -> AsyncGenerator[T, None]:
        return self

    async def __anext__(self) -> T:
        try:
            return await self.discover_next()
        except asyncio.TimeoutError:
            raise StopAsyncIteration

    async def __discover_generator(self) -> AsyncGenerator[BLEDevice, None]:
        async for ble_device, _ in self.__scanner.advertisement_data():
            yield ble_device

    def __is_valid_device(self, ble_device: BLEDevice) -> bool:
        device_name = ble_device.name
        device_address = ble_device.address

        return (device_name
                and any(name.value in device_name for name in self.__devices_names)
                and device_address not in self.__discovered_devices)

    async def discover_next(self, timeout: Optional[int] = None) -> T:
        """
        This method is used to discover the next valid BLE device. It first sets the timeout value to the provided argument or
        the default timeout value if no argument is provided. Then, it enters a loop that continues until a valid device
        is found or a timeout error occurs.

        :param timeout: Optional timeout value in seconds. If not provided, the default timeout value is used.
        :return: An instance of the device class for the first valid device found.
        """
        timeout = timeout or self.__timeout

        try:
            async with asyncio.timeout(timeout):
                async for ble_device in self.__generator:
                    if self.__is_valid_device(ble_device):
                        logger.info(f"Found {ble_device.name} ({ble_device.address})")

                        neuroplay_device = self.__device_class(ble_device)
                        self.__discovered_devices[ble_device.address] = neuroplay_device

                        return neuroplay_device
        except asyncio.TimeoutError as e:
            logger.info(f"Timeout reached ({timeout}s)., stop discovering.")
            raise e

    @staticmethod
    async def search_for(device_type: NeuroPlayDevicesEnum,
                         device_id: int,
                         device_class: Type[T] = NeuroPlayDevice,
                         timeout: int = 5) -> Optional[T]:
        pattern = rf'^{re.escape(device_type.value)}.* \({device_id}\)$'

        async with NeuroPlayScanner(devices_names={device_type}, timeout=timeout, device_class=device_class) as scanner:
            async for device in scanner:
                if re.match(pattern, device.full_name):
                    return device

        return None

    @property
    def discovered_devices(self) -> List[T]:
        return list(self.__discovered_devices.values())

    def clear_discovered_devices(self) -> None:
        self.__discovered_devices.clear()

    async def start(self) -> None:
        await self.__scanner.start()

    async def stop(self) -> None:
        await self.__scanner.stop()

    def asend(self, __value):
        raise NotImplementedError

    def athrow(self, __typ, __val=None, __tb=None):
        raise NotImplementedError
