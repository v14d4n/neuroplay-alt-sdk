import logging
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

import pyedflib
from pyedflib import EdfWriter
from typing import List, Optional, Any

from ..csv import CSVAnnotationsWriter, CSVDataWriter, CSVUtil

logger = logging.getLogger(__name__)


class EDFCreator:
    def __init__(self, channels_names: List[str], sampling_rate: int):
        self.__channels_names = channels_names
        self.__sample_frequency = sampling_rate
        self.__csv_data_writer: CSVDataWriter = CSVDataWriter(columns_names=channels_names)
        self.__csv_annotations_writer: CSVAnnotationsWriter = CSVAnnotationsWriter()
        self.__buffer = []

        self.__path_to_edf: Optional[Path] = None
        self.__path_to_data_csv: Optional[Path] = None
        self.__path_to_annotations_csv: Optional[Path] = None

        self.__is_recording = False
        self.__start_time: Optional[float] = None
        self.__on_stop_recording_callables: list[Callable[[], Any]] = []
        self.__on_start_recording_callables: list[Callable[[], Any]] = []

    def start_recording(self, output_edf_path: Path) -> None:
        """
        :param output_edf_path: Path to EDF file that will be created.
        :raises RuntimeError: Raises if recording is already started.
        :return None:
        """
        if self.__is_recording:
            raise RuntimeError('Recording is already started.')

        for call in self.__on_start_recording_callables:
            call()

        self.__is_recording = True

        self.__path_to_edf = output_edf_path

        self.__path_to_annotations_csv = output_edf_path.parent.joinpath('annotations.csv')
        self.__path_to_data_csv = output_edf_path.parent.joinpath('data.csv')

        start_time = self.__csv_data_writer.start_writing(self.__path_to_data_csv)
        self.__csv_annotations_writer.start_writing(self.__path_to_annotations_csv, start_time)

    def stop_recording(self) -> None:
        """
        :raises RuntimeError: Raises if recording is not started.
        :return None:
        """
        if not self.__is_recording:
            raise RuntimeError('Recording is not started.')

        for call in self.__on_stop_recording_callables:
            call()

        if self.__buffer:
            self.__csv_data_writer.append_rows(self.__buffer)
            self.__buffer.clear()

        self.__csv_annotations_writer.stop_writing()
        self.__csv_data_writer.stop_writing()

        EDFCreator.save_csv_as_edf(
            file_path_edf=self.__path_to_edf,
            file_path_csv_data=self.__path_to_data_csv,
            file_path_csv_annotations=self.__path_to_annotations_csv,
            sample_frequency=self.__sample_frequency,
        )

        self.__path_to_edf = None
        self.__path_to_data_csv = None
        self.__path_to_annotations_csv = None
        self.__start_time = None
        self.__is_recording = False

    def write_annotation(self, text: str) -> None:
        """
        :raises RuntimeError: Raises if recording is not started.
        :return None:
        """
        if not self.__is_recording:
            raise RuntimeError('Recording is not started.')

        self.__csv_annotations_writer.append_annotation(text)

    @staticmethod
    def save_csv_as_edf(
            file_path_csv_data: Path,
            file_path_edf: Path,
            sample_frequency: int,
            file_path_csv_annotations: Path = None,
    ) -> None:
        """
        :param file_path_csv_data:
        :param file_path_edf:
        :param sample_frequency:
        :param file_path_csv_annotations:
        :raises pd.errors.EmptyDataError: Raises if CSV file does not have time or text columns.
        :raises ValueError: Raises if pandas cannot convert time to float or text to str.
        :return None:
        """
        column_names = CSVUtil.get_column_names(file_path_csv_data)

        edf_writer = EdfWriter(
            str(file_path_edf),
            len(column_names),
            file_type=pyedflib.FILETYPE_EDFPLUS
        )

        for i, label in enumerate(column_names):
            edf_writer.setSignalHeader(i, {
                'label': label,
                'dimension': 'uV',
                'sample_frequency': sample_frequency,
                'physical_min': -10000.0,
                'physical_max': 10000.0,
                'digital_min': -32768,
                'digital_max': 32767,
            })

        data = CSVUtil.read_columns_values_as_numpy_array(file_path_csv_data)

        logger.info(f'Writing data to EDF file: {file_path_csv_data} -> {file_path_edf}')
        edf_writer.writeSamples(data)
        logger.info(f'Data is wrote to EDF file: {file_path_csv_data} -> {file_path_edf}')

        if file_path_csv_annotations:
            try:
                df = pd.read_csv(str(file_path_csv_annotations), encoding='utf-8', header=0, names=['time', 'text'])
            except pd.errors.EmptyDataError as e:
                raise e

            try:
                df['time'] = df['time'].astype(float)
                df['text'] = df['text'].astype(str)
            except ValueError:
                raise ValueError("Cannot convert time to float or text to str.")

            for index, row in df.iterrows():
                annotation_time = float(row['time'])
                annotation_text = str(row['text'])

                edf_writer.writeAnnotation(annotation_time, 0, annotation_text)

        edf_writer.close()

    def write_data(self, data: np.ndarray):
        self.__buffer.append(data)

        if len(self.__buffer) >= self.__sample_frequency:
            self.__csv_data_writer.append_rows(self.__buffer)
            self.__buffer.clear()

    @property
    def is_recording(self) -> bool:
        return self.__is_recording

    @property
    def csv_data_writer(self) -> CSVDataWriter:
        return self.__csv_data_writer

    @property
    def csv_annotations_writer(self) -> CSVAnnotationsWriter:
        return self.__csv_annotations_writer

    @property
    def on_stop_recording_callables(self) -> list[Callable[[], Any]]:
        return self.__on_stop_recording_callables

    @property
    def on_start_recording_callables(self) -> list[Callable[[], Any]]:
        return self.__on_start_recording_callables
