import h5py
import numpy as np

from typing import Union

class Data:
    def __init__(self, filepath: str, name: str):
        self.filepath = filepath
        self.name = name
        self._data_dict = {}

    def get_hdf5_data(self) -> dict:
        d = {}
        with h5py.File(self.filepath, "r") as f:
            d[self.name] = f["DATA"][:].T
            _N1, _N2 = d[self.name].shape

            x1 = f["AXIS"]["X1 AXIS"][:]
            x2 = f["AXIS"]["X2 AXIS"][:]
            
            dx1 = (x1[1] - x1[0]) / _N1
            dx2 = (x2[1] - x2[0]) / _N2
            
            d[f"{self.name}_x"] = dx1 * np.arange(_N1) + dx1 / 2 + x1[0]
            d[f"{self.name}_y"] = dx2 * np.arange(_N2) + dx2 / 2 + x2[0]
            d[f"{self.name}_xlim"] = x1
            d[f"{self.name}_ylim"] = x2

        return d

    @property
    def data_dict(self) -> dict:
        if not self._data_dict:
            self._data_dict = self.get_hdf5_data()
        return self._data_dict

    def get_property(self, prop: str) -> np.array:
        return self.data_dict[f"{self.name}{prop}"]

    @property
    def data(self) -> np.array:
        return self.get_property("")

    @property
    def xdata(self) -> np.array:
        return self.get_property("_x")

    @property
    def ydata(self) -> np.array:
        return self.get_property("_y")

    @property
    def xlimdata(self) -> np.array:
        return self.get_property("_xlim")

    @property
    def ylimdata(self) -> np.array:
        return self.get_property("_ylim")


class Field(Data):
    def __init__(self, filepath: str, name: str, origin: str):
        super().__init__(filepath, name)
        self.origin = origin # e.g., "External"


class Phase(Data):
    def __init__(self, filepath: str, name: str, species: Union[int, str]):
        super().__init__(filepath, name)
        self.species = species