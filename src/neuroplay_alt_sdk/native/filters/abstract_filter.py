from abc import abstractmethod, ABC


class AbstractFilter(ABC):
    @abstractmethod
    def apply_filter(self, data_sample):
        return data_sample
