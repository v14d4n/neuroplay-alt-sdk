import csv
import logging
from typing import Iterable

from . import AbstractCSVWriter

logger = logging.getLogger(__name__)


class CSVDataWriter(AbstractCSVWriter):
    def append_rows(self, data: Iterable[Iterable]) -> None:
        """
        :param data: Data to be appended to the CSV file.
        :raises RuntimeError: If recording is not started.
        :return None:
        """
        if self.__is_recording:
            with self.__csv_file_path.open('a', newline='', encoding='utf-8') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerows(data)
            logger.debug(f'Appended data to csv file (path: {self.__csv_file_path})')
        else:
            raise RuntimeError('Recording is not started.')
