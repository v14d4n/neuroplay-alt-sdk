import numpy as np
from scipy.signal import butter, lfilter

from .abstract_filter import AbstractFilter


class ContinuousFilter(AbstractFilter):
    def __init__(self, cutoff, fs, btype, order=5):
        self.cutoff = cutoff
        self.fs = fs
        self.order = order
        self.b, self.a = butter(self.order, self.cutoff / (0.5 * fs), btype)
        self.zi = np.zeros(max(len(self.a), len(self.b)) - 1)

    def apply_filter(self, data_sample):
        filtered_sample, self.zi = lfilter(self.b, self.a, [data_sample], zi=self.zi)
        return filtered_sample[0]
