import asyncio
from typing import List, Sequence, Dict

import numpy as np
from bleak import BLEDevice

from .abstract_neuroplay_device import AbstractNeuroPlayDevice
from ..edf import EDFCreator
from ..enums import DataStatusEnum
from ..filters import ContinuousFilter, ContinuousNotchFilter, FiltersContainer
from ..utils import DataSynchronizer


class NeuroPlayDevice(AbstractNeuroPlayDevice):
    def __init__(self, ble_device: BLEDevice):
        super().__init__(ble_device)
        self.__channels_filters = []
        for i in range(self.channels_count):
            filter_container = FiltersContainer()
            filter_container.add_filter(ContinuousFilter(2, self.sampling_rate, 'high'))
            filter_container.add_filter(ContinuousFilter(40, self.sampling_rate, 'low'))
            filter_container.add_filter(ContinuousNotchFilter(50, self.sampling_rate))
            self.__channels_filters.append(filter_container)
        self.__edf_creator = EDFCreator(self.channels_names, self.sampling_rate)

        self.__valid_buffer = []
        self.__accumulating_event = asyncio.Event()
        self.__accumulating_completed = asyncio.Event()
        self.__validate_lock = asyncio.Lock()
        self.__is_channels_valid: Dict[str, DataStatusEnum] = {
            channel: DataStatusEnum.NOT_VALID for channel in self.channels_names
        }

        self.__data_synchronizer = DataSynchronizer(self.sampling_rate)
        self.__edf_creator.on_start_recording_callables.append(self.__data_synchronizer.reset)

    async def filter_sample_data(self, data: List[float]) -> Sequence[float]:
        filtered_data = []
        for f, data in zip(self.__channels_filters, data):
            filtered_data.append(f.apply_filter(data))
        return filtered_data

    async def raw_channels_data_handler(self, data: List[float]) -> None:
        pass

    async def filtered_channels_data_handler(self, data: Sequence[float]) -> None:
        if self.__edf_creator.is_recording:
            for timed_data in self.__data_synchronizer.synchronize_data(data):
                self.__edf_creator.write_data(np.array(timed_data))

        if self.__accumulating_event.is_set():
            self.__valid_buffer.append(data)
            if len(self.__valid_buffer) >= self.sampling_rate:
                await self.__complete_accumulation()

    async def on_disconnected(self) -> None:
        self.__data_synchronizer.reset()

    async def validate_channels(self) -> Dict[str, DataStatusEnum]:
        """
        :raises RuntimeError: Raises if device is not connected.
        :return Dict[str, NeuroPlayDataStatusEnum]:
        """
        async with self.__validate_lock:
            if not self.is_connected:
                raise RuntimeError("Neuroplay device is not connected.")

            self.__start_accumulation()

            try:
                await asyncio.wait_for(self.__accumulating_completed.wait(), timeout=5)
            except asyncio.TimeoutError as e:
                self.__reset_accumulation()
                raise RuntimeError("Neuroplay device is not connected.")

            if not self.is_connected:
                self.__reset_accumulation()
                raise RuntimeError("Neuroplay device is not connected.")

            data = await self.__validate_channels_data_from_buffer()
            self.__reset_accumulation()

            return data

    async def __validate_channels_data_from_buffer(self) -> dict[str, DataStatusEnum]:
        valid_array = np.array(self.__valid_buffer).T

        max_deviations = []

        for i in range(valid_array.shape[0]):
            max_value = np.max(valid_array[i])
            min_value = np.min(valid_array[i])
            max_deviations.append(max(abs(max_value), abs(min_value)))

        return {
            channel: (
                DataStatusEnum.VALID if max_deviation <= 250 else
                DataStatusEnum.NOT_VALID if max_deviation > 1000 else
                DataStatusEnum.WARN
            )
            for channel, max_deviation in zip(self.channels_names, max_deviations)
        }

    async def __complete_accumulation(self) -> None:
        self.__accumulating_event.clear()
        self.__accumulating_completed.set()

    def __start_accumulation(self) -> None:
        self.__accumulating_event.set()

    def __reset_accumulation(self) -> None:
        self.__valid_buffer.clear()
        self.__accumulating_completed.clear()

    @property
    def edf_creator(self) -> EDFCreator:
        return self.__edf_creator
