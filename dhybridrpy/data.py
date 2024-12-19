import h5py
import numpy as np
import dask.array as da
import matplotlib.pyplot as plt

from matplotlib.axes import Axes
from matplotlib.collections import QuadMesh
from typing import Tuple
from dask import delayed

class Data:
    def __init__(self, file_path: str, name: str, timestep: int, lazy_evaluate: bool):
        self.file_path = file_path
        self.name = name
        self.timestep = timestep
        self.lazy_evaluate = lazy_evaluate
        self._data_dict = {}
        self._data_shape = None

    def _get_coordinate_limits(self, axis_name: str) -> np.ndarray | da.Array:
        """Retrieve a specific axis from the file."""
        if axis_name not in self._data_dict:

            def coordinate_limits_helper() -> np.ndarray:
                with h5py.File(self.file_path, "r") as file:
                    return file["AXIS"][axis_name][:]

            if self.lazy_evaluate:
                self._data_dict[axis_name] = da.from_array(coordinate_limits_helper(), chunks="auto")
            else:
                self._data_dict[axis_name] = coordinate_limits_helper()

        return self._data_dict[axis_name]

    def _compute_coordinates(self, axis_name: str, size: int) -> np.ndarray | da.Array:
        """Compute coordinates for a given axis."""
        key = f"{axis_name} coords"
        if key not in self._data_dict:
            axis_limits = self._get_coordinate_limits(axis_name)
            delta = (axis_limits[1] - axis_limits[0]) / size
            if self.lazy_evaluate:
                grid = da.arange(size, chunks="auto")
            else:
                grid = np.arange(size)
            self._data_dict[key] = delta*grid + (delta/2) + axis_limits[0]
        return self._data_dict[key]
    
    def _get_data_shape(self) -> tuple:
        """Retrieve the shape of the data without loading it."""
        if not self._data_shape:
            with h5py.File(self.file_path, "r") as file:
                self._data_shape = file["DATA"].shape
        return self._data_shape

    @property
    def data(self) -> np.ndarray | da.Array:
        """Retrieve the data values."""
        if self.name not in self._data_dict:

            def data_helper() -> np.ndarray:
                """Load the data from the file."""
                with h5py.File(self.file_path, "r") as file:
                    return file["DATA"][:].T

            if self.lazy_evaluate:
                self._data_dict[self.name] = da.from_array(data_helper(), chunks="auto")
            else:
                self._data_dict[self.name] = data_helper()
        return self._data_dict[self.name]
   

    @property
    def xdata(self) -> np.ndarray | da.Array:
        """Retrieve x-coordinates."""
        return self._compute_coordinates("X1 AXIS", self._get_data_shape()[0])

    @property
    def ydata(self) -> np.ndarray | da.Array:
        """Retrieve y-coordinates."""
        return self._compute_coordinates("X2 AXIS", self._get_data_shape()[1])

    @property
    def xlimdata(self) -> np.ndarray | da.Array:
        """Retrieve x-axis limits."""
        return self._get_coordinate_limits("X1 AXIS")

    @property
    def ylimdata(self) -> np.ndarray | da.Array:
        """Retrieve y-axis limits."""
        return self._get_coordinate_limits("X2 AXIS")

    def plot(self, 
        ax: Axes | None = None,
        dpi: int = 100,
        title: str | None = None,
        xlabel: str = r"$x$",
        ylabel: str = r"$y$",
        xlim: tuple | None = None,
        ylim: tuple | None = None,
        colormap: str = "viridis",
        show_colorbar: bool = True,
        colorbar_label: str | None = None,
        # save: bool = False,
        # save_name: str | None = None,
        # save_format: str = "jpg",
        # show: bool = True,
        **kwargs
    ) -> Tuple[Axes, QuadMesh]:

        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 6), dpi=dpi)

        X, Y = np.meshgrid(self.xdata, self.ydata, indexing="ij")
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

        # if save:
        #     if not save_name:
        #         save_name = f"{self.name}_timestep{self.timestep}"
        #     plt.savefig(f"{save_name}.{save_format}", dpi=dpi)

        # if show:
        #     plt.show()

        return ax, mesh

    def __repr__(self) -> str:
        attrs = ", ".join(
            f"{attr}={value}" for attr, value in self.__dict__.items() if not attr.startswith("_")
        )
        return f"{self.__class__.__name__}({attrs})"


class Field(Data):
    def __init__(self, file_path: str, name: str, timestep: int, lazy_evaluate: bool, origin: str):
        super().__init__(file_path, name, timestep, lazy_evaluate)
        self.origin = origin # e.g., "External"


class Phase(Data):
    def __init__(self, file_path: str, name: str, timestep: int, lazy_evaluate: bool, species: int | str):
        super().__init__(file_path, name, timestep, lazy_evaluate)
        self.species = species