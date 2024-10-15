import time
from typing import Optional, Sequence


class DataSynchronizer:
    def __init__(self, sampling_rate: int = 125):
        self.__first_run: bool = True
        self.__expected_time_limit: Optional[float] = None
        self.__interval: float = 1 / sampling_rate

    def synchronize_data(self, data: Sequence[float]) -> list[Sequence[float]]:
        current_time = time.perf_counter()

        if self.__first_run:
            self.__first_run = False
            self.__expected_time_limit = time.perf_counter()

        self.__expected_time_limit += self.__interval
        buffer: list[Sequence[float]] = []

        if self.__expected_time_limit >= current_time:
            buffer.append(data)
        else:
            while self.__expected_time_limit < current_time:
                self.__expected_time_limit += self.__interval
                buffer.append([.0] * len(data))
            buffer.append(data)

        return buffer

    def reset(self):
        self.__first_run = True
        self.__expected_time_limit = None
