import h5py
import numpy as np
import dask.array as da
import matplotlib.pyplot as plt

from matplotlib.axes import Axes
from matplotlib.collections import QuadMesh
from typing import Tuple
from dask.delayed import delayed

class BaseProperties:
    def __init__(self, file_path: str, name: str, timestep: int, lazy: bool):
        self.file_path = file_path
        self.name = name
        self.timestep = timestep
        self.lazy = lazy
        self._data_dict = {}

    def __repr__(self) -> str:
        attrs = ", ".join(
            f"{attr}={value}" for attr, value in self.__dict__.items() if not attr.startswith("_")
        )
        return f"{self.__class__.__name__}({attrs})"


class Data(BaseProperties):
    def __init__(self, file_path: str, name: str, timestep: int, lazy: bool):
        super().__init__(file_path, name, timestep, lazy)
        self._data_shape = None
        self._data_dtype = None

    def _get_coordinate_limits(self, axis_name: str) -> np.ndarray:
        if axis_name not in self._data_dict:
            with h5py.File(self.file_path, "r") as file:
                self._data_dict[axis_name] = file["AXIS"][axis_name][:]
        return self._data_dict[axis_name]

    def _compute_coordinates(self, axis_name: str, size: int) -> np.ndarray | da.Array:
        key = f"{axis_name} coords"
        if key not in self._data_dict:
            axis_limits = self._get_coordinate_limits(axis_name)
            delta = (axis_limits[1] - axis_limits[0]) / size
            grid = da.arange(size, chunks="auto") if self.lazy else np.arange(size)
            self._data_dict[key] = delta*grid + (delta/2) + axis_limits[0]
        return self._data_dict[key]
    
    def _get_data_shape(self) -> tuple:
        """Retrieve the shape of the data without loading it."""
        if self._data_shape is None:
            with h5py.File(self.file_path, "r") as file:
                # Reverse the data shape to be consistent with transpose in data @property
                self._data_shape = file["DATA"].shape[::-1]
        return self._data_shape

    def _get_data_dtype(self) -> np.dtype:
        if self._data_dtype is None:
            with h5py.File(self.file_path, "r") as file:
                self._data_dtype = file["DATA"].dtype
        return self._data_dtype

    @property
    def data(self) -> np.ndarray | da.Array:
        """Retrieves the field / phase values. Rows correspond to x-values, columns correspond to y-values."""
        if self.name not in self._data_dict:

            def data_helper() -> np.ndarray:
                with h5py.File(self.file_path, "r") as file:
                    return file["DATA"][:].T

            if self.lazy:
                delayed_helper = delayed(data_helper)()
                self._data_dict[self.name] = da.from_delayed(
                    delayed_helper, shape=self._get_data_shape(), dtype=self._get_data_dtype()
                )
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
        **kwargs
    ) -> Tuple[Axes, QuadMesh]:

        if len(self._get_data_shape()) != 2:
            raise NotImplementedError("Plotting is currently restricted to 2D data.")

        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 6), dpi=dpi)

        if self.lazy:
            data, xdata, ydata, xlimdata, ylimdata = (
                self.data.compute(),
                self.xdata.compute(), 
                self.ydata.compute(), 
                self.xlimdata.compute(), 
                self.ylimdata.compute()
            )
        else:
            data, xdata, ydata, xlimdata, ylimdata = (
                self.data, 
                self.xdata, 
                self.ydata, 
                self.xlimdata, 
                self.ylimdata
            )

        X, Y = np.meshgrid(xdata, ydata, indexing="ij")
        mesh = ax.pcolormesh(
            X, Y, data, cmap=colormap, shading="auto", **kwargs
        )
        ax.set_title(title if title else f"{self.name} at timestep {self.timestep}")
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_xlim(xlim if xlim else xlimdata)
        ax.set_ylim(ylim if ylim else ylimdata)
        if show_colorbar:
            cbar = plt.colorbar(mesh, ax=ax)
            cbar.set_label(colorbar_label if colorbar_label else f"{self.name}")

        return ax, mesh


class Field(Data):
    def __init__(self, file_path: str, name: str, timestep: int, lazy: bool, origin: str):
        super().__init__(file_path, name, timestep, lazy)
        self.origin = origin # e.g., "External"


class Phase(Data):
    def __init__(self, file_path: str, name: str, timestep: int, lazy: bool, species: int | str):
        super().__init__(file_path, name, timestep, lazy)
        self.species = species


class Raw(BaseProperties):
    def __init__(self, file_path: str, name: str, timestep: int, lazy: bool, species: int):
        super().__init__(file_path, name, timestep, lazy)
        self.species = species

    @property
    def dict(self) -> dict:
        if not self._data_dict:
            with h5py.File(self.file_path, "r") as file:
                def dict_helper():
                    with h5py.File(self.file_path, "r") as f:
                        return f[key][:]

                for key in file.keys():
                    if self.lazy:
                        shape = file[key].shape
                        dtype = file[key].dtype
                        delayed_helper = delayed(dict_helper)()
                        self._data_dict[key] = da.from_delayed(delayed_helper, shape=shape, dtype=dtype)
                    else:
                        self._data_dict[key] = file[key][:]
        return self._data_dict