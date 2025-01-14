import h5py
import numpy as np
import dask.array as da
import matplotlib.pyplot as plt
from collections import defaultdict

from matplotlib.axes import Axes
from matplotlib.collections import QuadMesh, PathCollection
from matplotlib.lines import Line2D
from typing import Tuple, Union, Optional
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

    _LABEL_MAPPINGS = defaultdict(lambda: ("$x$", "$y$"), {
        "p1x1": ("$x$", "$p_x$"), "p1x2": ("$y$", "$p_x$"), "p1x3": ("$z$", "$p_x$"),
        "p2x1": ("$x$", "$p_y$"), "p2x2": ("$y$", "$p_y$"), "p2x3": ("$z$", "$p_y$"),
        "p3x1": ("$x$", "$p_z$"), "p3x2": ("$y$", "$p_z$"), "p3x3": ("$z$", "$p_z$"),
        "ptx1": ("$x$", "$p_{tot}$"), "ptx2": ("$y$", "$p_{tot}$"), "ptx3": ("$z$", "$p_{tot}$"),
        "etx1": ("$x$", "$e_{tot}$"), "etx2": ("$y$", "$e_{tot}$"), "etx3": ("$z$", "$e_{tot}$")
    })

    def __init__(self, file_path: str, name: str, timestep: int, lazy: bool):
        super().__init__(file_path, name, timestep, lazy)
        self._plot_title = f"{name} at timestep {timestep}"
        self._data_shape = None
        self._data_dtype = None

    def _get_coordinate_limits(self, axis_name: str) -> np.ndarray:
        if axis_name not in self._data_dict:
            with h5py.File(self.file_path, "r") as file:
                self._data_dict[axis_name] = file["AXIS"][axis_name][:]
        return self._data_dict[axis_name]

    def _compute_coordinates(self, axis_name: str, size: int) -> Union[np.ndarray, da.Array]:
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
        """Retrieve the type of the data without loading it."""
        if self._data_dtype is None:
            with h5py.File(self.file_path, "r") as file:
                self._data_dtype = file["DATA"].dtype
        return self._data_dtype

    @property
    def data(self) -> Union[np.ndarray, da.Array]:
        """Retrieve the data values at each grid point. In 2D, rows correspond to x-values and 
        columns correspond to y-values."""
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
    def xdata(self) -> Union[np.ndarray, da.Array]:
        """Retrieve the grid x (i.e. X1) coordinates."""
        return self._compute_coordinates("X1 AXIS", self._get_data_shape()[0])

    @property
    def ydata(self) -> Union[np.ndarray, da.Array]:
        """Retrieve the grid y (i.e. X2) coordinates."""
        return self._compute_coordinates("X2 AXIS", self._get_data_shape()[1])

    @property
    def zdata(self) -> Union[np.ndarray, da.Array]:
        """Retrieve the grid z (i.e. X3) coordinates."""
        return self._compute_coordinates("X3 AXIS", self._get_data_shape()[2])

    @property
    def xlimdata(self) -> Union[np.ndarray, da.Array]:
        """Retrieve the grid x (i.e. X1) axis limits."""
        return self._get_coordinate_limits("X1 AXIS")

    @property
    def ylimdata(self) -> Union[np.ndarray, da.Array]:
        """Retrieve the grid y (i.e. X2) axis limits."""
        return self._get_coordinate_limits("X2 AXIS")

    @property
    def zlimdata(self) -> Union[np.ndarray, da.Array]:
        """Retrieve the grid z (i.e. X3) axis limits."""
        return self._get_coordinate_limits("X3 AXIS")

    def plot(self,
        *,
        ax: Optional[Axes] = None,
        dpi: int = 100,
        title: Optional[str] = None,
        xlabel: Optional[str] = None,
        ylabel: Optional[str] = None,
        zlabel: Optional[str] = None,
        xlim: Optional[tuple] = None,
        ylim: Optional[tuple] = None,
        zlim: Optional[tuple] = None,
        colormap: str = "viridis",
        show_colorbar: bool = True,
        colorbar_label: Optional[str] = None,
        **kwargs
    ) -> Tuple[Axes, Union[Line2D, QuadMesh, PathCollection]]:
        """Plot the data."""

        num_dimensions = len(self._get_data_shape())
        if not 1 <= num_dimensions <= 3:
            raise NotImplementedError("Plotting is restricted to 1D, 2D, or 3D data.")

        if ax is None:
            if 1 <= num_dimensions <= 2:
                fig, ax = plt.subplots(figsize=(8,6), dpi=dpi)
            else:
                fig = plt.figure(figsize=(8,6), dpi=dpi)
                ax = fig.add_subplot(111, projection="3d")

        def is_computable(arr: Union[np.ndarray, da.Array]) -> bool:
            return self.lazy and isinstance(arr, da.Array)

        data = self.data.compute() if is_computable(self.data) else self.data
        xdata = self.xdata.compute() if is_computable(self.xdata) else self.xdata
        xlimdata = self.xlimdata.compute() if is_computable(self.xlimdata) else self.xlimdata

        if num_dimensions == 1:

            line = ax.plot(xdata, data, **kwargs)[0]
            ax.set_title(title if title else self._plot_title)
            ax.set_xlabel(xlabel if xlabel else "$x$")
            ax.set_ylabel(f"{self.name}")
            ax.set_xlim(xlim if xlim else xlimdata)

            return ax, line

        elif num_dimensions == 2:

            ydata = self.ydata.compute() if is_computable(self.ydata) else self.ydata
            ylimdata = self.ylimdata.compute() if is_computable(self.ylimdata) else self.ylimdata

            X, Y = np.meshgrid(xdata, ydata, indexing="ij")
            mesh = ax.pcolormesh(
                X, Y, data, cmap=colormap, shading="auto", **kwargs
            )

            ax.set_title(title if title else self._plot_title)
            xlabel, ylabel = self._LABEL_MAPPINGS[self.name]
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
            ax.set_xlim(xlim if xlim else xlimdata)
            ax.set_ylim(ylim if ylim else ylimdata)
            if show_colorbar:
                cbar = plt.colorbar(mesh, ax=ax)
                cbar.set_label(colorbar_label if colorbar_label else f"{self.name}")

            return ax, mesh

        else:

            ydata = self.ydata.compute() if is_computable(self.ydata) else self.ydata
            ylimdata = self.ylimdata.compute() if is_computable(self.ylimdata) else self.ylimdata
            zdata = self.zdata.compute() if is_computable(self.zdata) else self.zdata
            zlimdata = self.zlimdata.compute() if is_computable(self.zlimdata) else self.zlimdata

            X, Y, Z = np.meshgrid(xdata, ydata, zdata, indexing="ij")
            scatter = ax.scatter(
                X.flatten(), Y.flatten(), Z.flatten(), c=data.flatten(), cmap=colormap, **kwargs
            )

            ax.set_title(title if title else self._plot_title)
            ax.set_xlabel(xlabel if xlabel else "$x$")
            ax.set_ylabel(ylabel if ylabel else "$y$")
            ax.set_zlabel(zlabel if zlabel else "$z$")
            ax.set_xlim(xlim if xlim else xlimdata)
            ax.set_ylim(ylim if ylim else ylimdata)
            ax.set_zlim(zlim if zlim else zlimdata)

            if show_colorbar:
                cbar = plt.colorbar(scatter, ax=ax, shrink=0.5, aspect=10)
                cbar.set_label(colorbar_label if colorbar_label else f"{self.name}")

            return ax, scatter


class Field(Data):
    def __init__(self, file_path: str, name: str, timestep: int, lazy: bool, origin: str):
        super().__init__(file_path, name, timestep, lazy)
        self.origin = origin # e.g., "External"

    def plot(self, **kwargs) -> Tuple[Axes, Union[Line2D, QuadMesh, PathCollection]]:
        origin_info = f" (origin = {self.origin})"
        if origin_info not in self._plot_title:
            self._plot_title += origin_info
        return super().plot(**kwargs)


class Phase(Data):
    def __init__(self, file_path: str, name: str, timestep: int, lazy: bool, species: Union[int, str]):
        super().__init__(file_path, name, timestep, lazy)
        self.species = species

    def plot(self, **kwargs) -> Tuple[Axes, Union[Line2D, QuadMesh, PathCollection]]:
        species_info = f" (species = {self.species})"
        if species_info not in self._plot_title:
            self._plot_title += species_info
        return super().plot(**kwargs)


class Raw(BaseProperties):
    def __init__(self, file_path: str, name: str, timestep: int, lazy: bool, species: int):
        super().__init__(file_path, name, timestep, lazy)
        self.species = species

    @property
    def dict(self) -> dict:
        """Retrieve a dictionary of the raw file's keys and values."""
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