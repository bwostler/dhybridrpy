import h5py
import numpy as np
import matplotlib.pyplot as plt
import copy

from typing import Union
from matplotlib.axes import Axes

class Data:
    def __init__(self, file_path: str, name: str, timestep: int):
        self.file_path = file_path
        self.name = name
        self.timestep = timestep
        self._data_dict = {}
        self._data_shape = None

    def _get_data(self) -> np.array:
        """Retrieve the data values from the file."""
        if self.name not in self._data_dict:
            with h5py.File(self.file_path, "r") as file:
                self._data_dict[self.name] = file["DATA"][:].T
        return self._data_dict[self.name]

    def _get_coordinate_limits(self, axis_name: str) -> np.array:
        """Retrieve a specific axis from the file."""
        if axis_name not in self._data_dict:
            with h5py.File(self.file_path, "r") as file:
                self._data_dict[axis_name] = file["AXIS"][axis_name][:]
        return self._data_dict[axis_name]

    def _compute_coordinates(self, axis_name: str, size: int) -> np.array:
        """Compute coordinates for a given axis."""
        key = f"{axis_name} coords"
        if key not in self._data_dict:
            axis_limits = self._get_coordinate_limits(axis_name)
            delta = (axis_limits[1] - axis_limits[0]) / size
            self._data_dict[key] = delta*np.arange(size) + (delta/2) + axis_limits[0]
        return self._data_dict[key]
    
    @property
    def data_shape(self) -> tuple:
        """Retrieve the shape of the data without loading it."""
        if not self._data_shape:
            with h5py.File(self.file_path, "r") as file:
                self._data_shape = file["DATA"].shape
        return self._data_shape

    @property
    def data(self) -> np.array:
        """Retrieve the data values."""
        return self._get_data()

    @property
    def xdata(self) -> np.array:
        """Retrieve x-coordinates."""
        return self._compute_coordinates("X1 AXIS", self.data_shape[0])

    @property
    def ydata(self) -> np.array:
        """Retrieve y-coordinates."""
        return self._compute_coordinates("X2 AXIS", self.data_shape[1])

    @property
    def xlimdata(self) -> np.array:
        """Retrieve x-axis limits."""
        return self._get_coordinate_limits("X1 AXIS")

    @property
    def ylimdata(self) -> np.array:
        """Retrieve y-axis limits."""
        return self._get_coordinate_limits("X2 AXIS")

    def plot(self, 
            ax: Axes = None,
            dpi: int = 100,
            title: str = None,
            xlabel: str = r"$x$",
            ylabel: str = r"$y$",
            xlim: tuple = None,
            ylim: tuple = None,
            colormap: str = "viridis",
            show_colorbar: bool = True,
            colorbar_label: str = None,
            save: bool = False,
            save_name: str = None,
            save_format: str = "jpg",
            show: bool = True,
            **kwargs
        ) -> Axes:

        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 6), dpi=dpi)

        X, Y = np.meshgrid(self.xdata, self.ydata, indexing='ij')
        mesh = ax.pcolormesh(
            X, Y, self.data, cmap=colormap, shading="auto", **kwargs
        )
        ax.set_title(title if title else f"{self.name} at timestep {self.timestep}")
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_xlim(xlim if xlim else self.xlimdata)
        ax.set_ylim(ylim if ylim else self.ylimdata)
        if show_colorbar:
            cbar = plt.colorbar(mesh, ax=ax)
            cbar.set_label(colorbar_label if colorbar_label else f"{self.name}")

        if save:
            if not save_name:
                save_name = f"{self.name}_timestep{self.timestep}"
            plt.savefig(f"{save_name}.{save_format}", dpi=dpi)

        if show:
            plt.show()

        return ax

    def __repr__(self):
        attrs = ", ".join(
            f"{attr}={value}" for attr, value in self.__dict__.items() if not attr.startswith("_")
        )
        return f"{self.__class__.__name__}({attrs})"


class Field(Data):
    def __init__(self, file_path: str, name: str, timestep: int, origin: str):
        super().__init__(file_path, name, timestep)
        self.origin = origin # e.g., "External"


class Phase(Data):
    def __init__(self, file_path: str, name: str, timestep: int, species: Union[int, str]):
        super().__init__(file_path, name, timestep)
        self.species = species