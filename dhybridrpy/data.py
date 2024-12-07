import h5py
import numpy as np
import matplotlib.pyplot as plt

from typing import Union
from matplotlib.axes import Axes

class Data:
    def __init__(self, filepath: str, name: str):
        self.filepath = filepath
        self.name = name
        self._data_dict = {}

    def _get_hdf5_data(self) -> dict:
        with h5py.File(self.filepath, "r") as file:
            data = file["DATA"][:].T
            x1lims, x2lims = file["AXIS"]["X1 AXIS"][:], file["AXIS"]["X2 AXIS"][:]
            N1, N2 = data.shape

            dx1 = (x1lims[1] - x1lims[0]) / N1
            dx2 = (x2lims[1] - x2lims[0]) / N2
            x_coords = dx1 * np.arange(N1) + dx1 / 2 + x1lims[0]
            y_coords = dx2 * np.arange(N2) + dx2 / 2 + x2lims[0]

            return {
                self.name: data,
                f"{self.name}_x": x_coords,
                f"{self.name}_y": y_coords,
                f"{self.name}_xlim": x1lims,
                f"{self.name}_ylim": x2lims
            }

    @property
    def data_dict(self) -> dict:
        if not self._data_dict:
            self._data_dict = self._get_hdf5_data()
        return self._data_dict

    def _get_property(self, prop: str) -> np.array:
        return self.data_dict[f"{self.name}{prop}"]

    @property
    def data(self) -> np.array:
        return self._get_property("")

    @property
    def xdata(self) -> np.array:
        return self._get_property("_x")

    @property
    def ydata(self) -> np.array:
        return self._get_property("_y")

    @property
    def xlimdata(self) -> np.array:
        return self._get_property("_xlim")

    @property
    def ylimdata(self) -> np.array:
        return self._get_property("_ylim")

    def plot(self, axis: Axes = None) -> None:
        if axis is None:
            fig, axis = plt.subplots(figsize=(8, 6))

        mesh = axis.pcolormesh(
            self.xdata,
            self.ydata,
            self.data.T,
            shading="auto"
        )
        axis.set_title(f"{self.name} data")
        axis.set_xlabel(r"$x$")
        axis.set_ylabel(r"$y$")
        cbar = plt.colorbar(mesh, ax=axis)
        cbar.set_label(f"{self.name}")
        plt.show()


class Field(Data):
    def __init__(self, filepath: str, name: str, origin: str):
        super().__init__(filepath, name)
        self.origin = origin # e.g., "External"


class Phase(Data):
    def __init__(self, filepath: str, name: str, species: Union[int, str]):
        super().__init__(filepath, name)
        self.species = species