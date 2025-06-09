import csv
import logging
import time
from pathlib import Path
from typing import Optional

from .abstract_csv_writer import AbstractCSVWriter

logger = logging.getLogger(__name__)


class CSVAnnotationsWriter(AbstractCSVWriter):
    COLUMN_NAMES: list[str] = ['time', 'text']

    def __init__(self):
        super().__init__(
            columns_names=CSVAnnotationsWriter.COLUMN_NAMES,
        )
        self.__start_time: Optional[float] = None

    def start_writing(self, path_to_csv_file: Path, start_time: Optional[float] = None) -> float:
        """
        :param path_to_csv_file: Path to CSV file that will be created.
        :param start_time: If 'None' then time.time() will be used.
        :return float: Time of recording started.
        """
        if start_time:
            self.__start_time = start_time
        else:
            self.__start_time = time.time()

        return super().start_writing(path_to_csv_file)

    def stop_writing(self) -> None:
        super().stop_writing()
        self.__start_time = None

    def append_annotation(self, text: str) -> None:
        """
        :param text: Text to be appended to the CSV file.
        :raises RuntimeError: If recording is not started.
        :return None:
        """
        if self._is_recording:
            with self._csv_file_path.open('a', newline='', encoding='utf-8') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow([time.time() - self.__start_time, text])
            logger.debug(f'Appended data to csv file (path: {self._csv_file_path})')
        else:
            raise RuntimeError('Recording is not started.')
