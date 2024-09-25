import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class CSVUtil:
    @staticmethod
    def read_columns_values_as_numpy_array(csv_file_path: Path) -> np.ndarray:
        logger.info(f'Reading data from csv file: {csv_file_path}')
        return pd.read_csv(csv_file_path, encoding='utf-8').values.T

    @staticmethod
    def get_column_names(csv_file_path: Path) -> list[str]:
        return pd.read_csv(csv_file_path, nrows=0, encoding='utf-8').columns.tolist()
