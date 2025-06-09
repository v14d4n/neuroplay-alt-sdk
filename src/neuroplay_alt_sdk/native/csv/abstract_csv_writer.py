import csv
import logging
import time
from abc import ABC
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class AbstractCSVWriter(ABC):
    def __init__(self, columns_names: List[str]):
        self._csv_file_path: Optional[Path] = None
        self._columns_names: List[str] = columns_names
        self._is_recording: bool = False

    def start_writing(self, path_to_csv_file: Path) -> float:
        """
        :param path_to_csv_file: Path to the csv file.
        :raises RuntimeError: If recording is already started.
        :return float: Time of recording started.
        """
        if not self._is_recording:
            self.__create_csv_file(path_to_csv_file)
            self._is_recording = True
            start_time = time.time()
            logger.info(f'Started writing CSV file: {path_to_csv_file}')
        else:
            raise RuntimeError('Recording is already started.')

        return start_time

    def stop_writing(self) -> None:
        """
        :raises RuntimeError: Raised if recording is not started.
        :return None:
        """
        if not self._is_recording:
            raise RuntimeError('Recording is not started.')

        logger.info(f'Stopped writing CSV file: {self._csv_file_path}')
        self._csv_file_path = None
        self._is_recording = False

    def __create_csv_file(self, path: Path):
        self._csv_file_path = path
        with self._csv_file_path.open('w', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(self._columns_names)
        logger.info(f'Created csv file ({self._csv_file_path}, columns: {self._columns_names}).')

    @property
    def is_recording(self):
        return self._is_recording
