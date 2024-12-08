import h5py
import numpy as np
import matplotlib.pyplot as plt

from typing import Union
from matplotlib.axes import Axes

class Data:
    def __init__(self, file_path: str, name: str, timestep: int):
        self.file_path = file_path
        self.name = name
        self.timestep = timestep
        self._data_dict = {}

    def _get_hdf5_data(self) -> dict:
        with h5py.File(self.file_path, "r") as file:
            data = file["DATA"][:].T
            x1lims = file["AXIS"]["X1 AXIS"][:]
            x2lims = file["AXIS"]["X2 AXIS"][:]
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

    def plot(self, 
        ax: Axes = None,
        title: str = None,
        xlabel: str = r"$x$",
        ylabel: str = r"$y$",
        xlim: tuple = None,
        ylim: tuple = None,
        dpi: int = 100,
        colormap: str = "viridis",
        colorbar_label: str = None,
        save_name: str = None,
        **kwargs
    ) -> None:

        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 6), dpi=dpi)

        mesh = ax.pcolormesh(
            self.xdata, self.ydata, self.data.T, cmap=colormap, shading="auto", **kwargs
        )
        ax.set_title(title if title else f"{self.name} data")
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_xlim(xlim if xlim else self.xlimdata)
        ax.set_ylim(ylim if ylim else self.ylimdata)
        cbar = plt.colorbar(mesh, ax=ax)
        cbar.set_label(colorbar_label if colorbar_label else f"{self.name}")

        if save_name:
            plt.savefig(f"{save_name}.png", dpi=dpi) # for debugging purposes
        else:
            plt.show()


class Field(Data):
    def __init__(self, file_path: str, name: str, timestep: int, origin: str):
        super().__init__(file_path, name, timestep)
        self.origin = origin # e.g., "External"


class Phase(Data):
    def __init__(self, file_path: str, name: str, timestep: int, species: Union[int, str]):
        super().__init__(file_path, name, timestep)
        self.species = species