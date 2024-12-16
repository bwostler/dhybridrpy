import h5py
import numpy as np
import matplotlib.pyplot as plt

from typing import Union
from matplotlib.axes import Axes

# class Data:
#     def __init__(self, file_path: str, name: str, timestep: int):
#         self.file_path = file_path
#         self.name = name
#         self.timestep = timestep
#         self._data_dict = {}

#     def _get_hdf5_data(self) -> dict:
#         with h5py.File(self.file_path, "r") as file:
#             data = file["DATA"][:].T
#             x1lims = file["AXIS"]["X1 AXIS"][:]
#             x2lims = file["AXIS"]["X2 AXIS"][:]
#             N1, N2 = data.shape

#             dx1 = (x1lims[1] - x1lims[0]) / N1
#             dx2 = (x2lims[1] - x2lims[0]) / N2
#             x_coords = dx1 * np.arange(N1) + dx1 / 2 + x1lims[0]
#             y_coords = dx2 * np.arange(N2) + dx2 / 2 + x2lims[0]

#             return {
#                 self.name: data,
#                 f"{self.name}_x": x_coords,
#                 f"{self.name}_y": y_coords,
#                 f"{self.name}_xlim": x1lims,
#                 f"{self.name}_ylim": x2lims
#             }

#     @property
#     def data_dict(self) -> dict:
#         if not self._data_dict:
#             self._data_dict = self._get_hdf5_data()
#         return self._data_dict

#     def _get_property(self, prop: str) -> np.array:
#         return self.data_dict[f"{self.name}{prop}"]

#     @property
#     def data(self) -> np.array:
#         return self._get_property("")

#     @property
#     def xdata(self) -> np.array:
#         return self._get_property("_x")

#     @property
#     def ydata(self) -> np.array:
#         return self._get_property("_y")

#     @property
#     def xlimdata(self) -> np.array:
#         return self._get_property("_xlim")

#     @property
#     def ylimdata(self) -> np.array:
#         return self._get_property("_ylim")

class Data:
    def __init__(self, file_path: str, name: str, timestep: int):
        self.file_path = file_path
        self.name = name
        self.timestep = timestep
        self._data_dict = {}
        self._data_shape = None

    def _get_hdf5_dataset(self):
        """Retrieve the entire dataset from the file."""
        if self.name not in self._data_dict:
            with h5py.File(self.file_path, "r") as file:
                self._data_dict[self.name] = file["DATA"][:].T
        return self._data_dict[self.name]

    def _get_hdf5_coordinate_axis(self, axis_name: str):
        """Retrieve a specific axis from the file."""
        if axis_name not in self._data_dict:
            with h5py.File(self.file_path, "r") as file:
                self._data_dict[axis_name] = file["AXIS"][axis_name][:]
        return self._data_dict[axis_name]

    def _compute_coordinates(self, axis_name: str, size: int) -> np.array:
        """Compute coordinates for a given axis."""
        key = f"{axis_name} coords"
        if key not in self._data_dict:
            axis_limits = self._get_hdf5_coordinate_axis(axis_name)
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
        """Retrieve the main dataset."""
        return self._get_hdf5_dataset()

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
        return self._get_hdf5_coordinate_axis("X1 AXIS")

    @property
    def ylimdata(self) -> np.array:
        """Retrieve y-axis limits."""
        return self._get_hdf5_coordinate_axis("X2 AXIS")

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

    def __repr__(self):
        return (
            f"Data(file_path='{self.file_path}', name='{self.name}', "
            f"timestep={self.timestep})"
        )


class Field(Data):
    def __init__(self, file_path: str, name: str, timestep: int, origin: str):
        super().__init__(file_path, name, timestep)
        self.origin = origin # e.g., "External"

    def __repr__(self):
        return (
            f"Field(file_path='{self.file_path}', name='{self.name}', "
            f"timestep={self.timestep}, origin='{self.origin}')"
        )

class Phase(Data):
    def __init__(self, file_path: str, name: str, timestep: int, species: Union[int, str]):
        super().__init__(file_path, name, timestep)
        self.species = species

    def __repr__(self):
        return (
            f"Phase(file_path='{self.file_path}', name='{self.name}', "
            f"timestep={self.timestep}, species={repr(self.species)})"
        )