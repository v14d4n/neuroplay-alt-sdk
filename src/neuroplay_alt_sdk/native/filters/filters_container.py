from typing import List

from .abstract_filter import AbstractFilter


class FiltersContainer(AbstractFilter):
    def __init__(self, filters: List[AbstractFilter] = None):
        if filters is None:
            filters = []

        self.__filters = filters

    def add_filter(self, f: AbstractFilter):
        self.__filters.append(f)

    def clear_filters(self):
        self.__filters.clear()

    def apply_filter(self, data: float):
        for f in self.__filters:
            data = f.apply_filter(data)

        return data
