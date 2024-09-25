import asyncio
import logging
import re
from abc import ABC, abstractmethod
from typing import Optional, List, Sequence, assert_never

import bleak.exc
import numpy as np
from bleak import BleakClient, BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.backends.service import BleakGATTService
from numpy import ndarray

from ..enums import NeuroPlayDevicesEnum
from ..exceptions import NeuroPlayExceptionNotValidDevice

logger = logging.getLogger(__name__)


class AbstractNeuroPlayDevice(ABC):
    def __init__(self, ble_device: BLEDevice):
        """
        :raises NeuroPlayExceptionNotValidDevice:
        """
        self.__full_name: str = ble_device.name
        self.__address: str = ble_device.address
        self.__device_client = BleakClient(ble_device, winrt=dict(use_cached_services=False))

        self.__BLUETOOTH_UUID_EEG: str = "f0001298-0451-4000-b000-000000000000"
        self.__BLUETOOTH_UUID_EEG_DATA: str = "f0001299-0451-4000-b000-000000000000"
        self.__BLUETOOTH_UUID_EEG_CONTROL: str = "f000129a-0451-4000-b000-000000000000"

        self.__MAGIC_MICROVOLTS_BIT = 0.000186265
        self.__QUEUE_SIZE = 4
        self.__PACKET_SIZE = 20

        self.__data_service: Optional[BleakGATTService] = None
        self.__data_read_characteristic: Optional[BleakGATTCharacteristic] = None
        self.__data_control_characteristic: Optional[BleakGATTCharacteristic] = None

        self.__SAMPLING_RATE: int = 125
        self.__packets_list: List[bytes] = []
        self.__is_connected: bool = False

        match = re.fullmatch(r'(.+)\s\((\d+)\)$', self.full_name)

        if not match:
            raise NeuroPlayExceptionNotValidDevice

        self.__name: str = match.group(1)
        self.__type: NeuroPlayDevicesEnum = NeuroPlayDevicesEnum.from_string(self.name)
        self.__id: int = match.group(2)

        match self.__type:
            case NeuroPlayDevicesEnum.NEUROPLAY_6C:
                self.channels_names = ["O1", "T3", "Fp1", "Fp2", "T4", "O2"]
            case NeuroPlayDevicesEnum.NEUROPLAY_8CAP:
                self.channels_names = ["O1", "P3", "C3", "F3", "F4", "C4", "P4", "O2"]
            case _ as unreachable:
                assert_never(unreachable)

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
        self.__packets_list.clear()

    @abstractmethod
    async def raw_channels_data_handler(self, packet: List[float]) -> None:
        pass

    @abstractmethod
    async def filtered_channels_data_handler(self, data: Sequence[float]) -> None:
        pass

    @abstractmethod
    async def filter_sample_data(self, data: List[float]) -> Sequence[float]:
        return data

    @abstractmethod
    async def on_disconnected(self) -> None:
        pass

    async def packet_handler(self, _, packet: bytearray):
        self.__packets_list.append(packet)

        # Накапливаем 4 пакета
        if not (len(self.__packets_list) == self.__QUEUE_SIZE):
            return

        if self.__packets_list[0][0] & 0x03:  # Проверяем ID пакета. Он должен быть 0.
            self.__packets_list.pop(0)  # Только 00 & 11 (0x03) будет выдавать 0.
            return

        # Тут начинается низкоуровневая магия.
        # Создаём массив из 24 элементов так как у нас будет всего 24 значения.
        raw_sample_values_array = np.zeros(24, dtype=np.float64)

        # Проходим по пакетам и извлекаем значения.
        # Берём 4 пакета (__QUEUE_SIZE) по 20 байт (первые 2 байта заголовок).
        for i, packet in enumerate(self.__packets_list):
            # Последовательно записываем 6 семплов по 3 бита для каждого из пакетов в raw_sample_values_array
            for j in range(6):
                offset = 2 + j * 3
                val = int.from_bytes(packet[offset:offset + 3] + bytes([0x00]), byteorder='big',
                                     signed=True) * self.__MAGIC_MICROVOLTS_BIT
                raw_sample_values_array[i * 6 + j] = val

        # Превращаем массив в матрицу, где chX - данные канала
        # [ch1, ch2, ch3, ch4, ch5, ch6, ch7, ch8]
        # [ch1, ch2, ch3, ch4, ch5, ch6, ch7, ch8]
        # [ch1, ch2, ch3, ch4, ch5, ch6, ch7, ch8]
        samples_packets: ndarray = raw_sample_values_array.reshape(3, 8)

        #  Удаляем лишние каналы для конкретного устройства
        match self.__type:
            case NeuroPlayDevicesEnum.NEUROPLAY_6C:
                samples_packets = np.delete(samples_packets, [6, 1], axis=1)
            case NeuroPlayDevicesEnum.NEUROPLAY_8CAP:
                pass
            case _ as unreachable:
                assert_never(unreachable)

        # Отправляем семплы в обработчики
        for sample in samples_packets:
            await asyncio.gather(
                self.raw_channels_data_handler(sample.tolist()),
                self.filtered_channels_data_handler(await self.filter_sample_data(sample.tolist())),
            )

        self.__packets_list.clear()

    async def connect(self) -> bool:
        """
        :raises RuntimeError: Raised if device is already connected.
        :return bool:
        """

        if self.__is_connected:
            raise RuntimeError('Device is already connected')

        try:
            await self.__device_client.connect()

            services = self.__device_client.services

            self.__data_service = next(
                (service for service in services if service.uuid == self.__BLUETOOTH_UUID_EEG), None
            )

            if not self.__data_service:
                logger.error(f"Can't find data service for {self.full_name}")
                return False

            characteristics_dict = {char.uuid: char for char in self.__data_service.characteristics}

            self.__data_control_characteristic = characteristics_dict.get(self.__BLUETOOTH_UUID_EEG_CONTROL)
            self.__data_read_characteristic = characteristics_dict.get(self.__BLUETOOTH_UUID_EEG_DATA)

            if not (self.__data_control_characteristic or self.__data_read_characteristic):
                logger.error(f"Can't find data or read characteristics for {self.full_name}")
                return False

            # Начинаем передачу данных отправляя [0x01, 0x00] на сервис BLUETOOTH_UUID_EEG_DATA .
            await self.__device_client.write_gatt_char(self.__BLUETOOTH_UUID_EEG_DATA, bytearray(b'\x01\x00'))

            # Посылаем данные для выставления количества каналов. [0x01, 0x01] - 8 каналов.
            await self.__device_client.write_gatt_char(self.__BLUETOOTH_UUID_EEG_CONTROL, bytearray(b'\x01\x01'))

            # Включаем прием нотификаций от сервиса BLUETOOTH_UUID_EEG_DATA.
            await self.__device_client.start_notify(self.__BLUETOOTH_UUID_EEG_DATA, self.packet_handler)

            self.__is_connected = True
            logger.info(f"Connected to {self.__full_name}")
            return True
        finally:
            if not (self.__data_service or self.__data_read_characteristic or self.__data_control_characteristic):
                self.__device_client = None
                self.__data_service = None
                self.__data_control_characteristic = None
                self.__data_read_characteristic = None

    async def disconnect(self) -> None:
        """
        :raises bleak.exc.BleakError: Raised when device is unreachable or something else.
        :raises RuntimeError: Raised when device is not connected.
        :return None:
        """
        if not self.__is_connected:
            raise RuntimeError('Device is not connected')

        logger.info(f"Disconnecting from {self.__full_name}")

        try:
            # Останавливаем передачу данных передавая [0x00, 0x00] на сервис BLUETOOTH_UUID_EEG_DATA
            await self.__device_client.write_gatt_char(self.__BLUETOOTH_UUID_EEG_DATA, bytearray(b'\x00\x00'))

            # Останавливаем нотификацию
            await self.__device_client.stop_notify(self.__BLUETOOTH_UUID_EEG_DATA)
        except bleak.exc.BleakError as e:
            logger.warning(str(e))
            # raise e
        finally:
            await self.__device_client.disconnect()
            self.__is_connected = False
            await self.on_disconnected()

        logger.info(f"Disconnected from {self.__full_name}")

    @property
    def is_connected(self) -> bool:
        return self.__is_connected

    @property
    def id(self) -> int:
        return self.__id

    @property
    def type(self) -> NeuroPlayDevicesEnum:
        return self.__type

    @property
    def name(self) -> str:
        return self.__name

    @property
    def full_name(self) -> str:
        return self.__full_name

    @property
    def address(self) -> str:
        return self.__address

    @property
    def channels_count(self) -> int:
        return len(self.channels_names)

    @property
    def sampling_rate(self) -> int:
        return self.__SAMPLING_RATE

    def __str__(self):
        return f'{self.__full_name} ({self.__address})'
