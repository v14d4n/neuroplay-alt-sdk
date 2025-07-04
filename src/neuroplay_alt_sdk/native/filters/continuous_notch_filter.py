import numpy as np
from scipy.signal import lfilter, iirnotch

from .abstract_filter import AbstractFilter


class ContinuousNotchFilter(AbstractFilter):
    def __init__(self, notch_freq, fs, quality_factor=30, order=2):
        self.notch_freq = notch_freq
        self.quality_factor = quality_factor
        self.fs = fs
        self.order = order
        self.b, self.a = iirnotch(w0=self.notch_freq / (0.5 * fs), Q=self.quality_factor)
        self.zi = np.zeros(max(len(self.a), len(self.b)) - 1)

    def apply_filter(self, data_sample):
        filtered_sample, self.zi = lfilter(self.b, self.a, [data_sample], zi=self.zi)
        return filtered_sample[0]
