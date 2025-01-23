import h5py
import numpy as np
import dask.array as da
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from collections import defaultdict

from matplotlib.axes import Axes
from matplotlib.collections import QuadMesh, PathCollection
from matplotlib.lines import Line2D
from typing import Tuple, Union, Optional, Literal
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
        """Retrieve the data at each grid point."""
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
        """Retrieve the x (i.e. X1) grid coordinates."""
        return self._compute_coordinates("X1 AXIS", self._get_data_shape()[0])

    @property
    def ydata(self) -> Union[np.ndarray, da.Array]:
        """Retrieve the y (i.e. X2) grid coordinates."""
        return self._compute_coordinates("X2 AXIS", self._get_data_shape()[1])

    @property
    def zdata(self) -> Union[np.ndarray, da.Array]:
        """Retrieve the z (i.e. X3) grid coordinates."""
        return self._compute_coordinates("X3 AXIS", self._get_data_shape()[2])

    @property
    def xlimdata(self) -> Union[np.ndarray, da.Array]:
        """Retrieve the x (i.e. X1) grid axis limits."""
        return self._get_coordinate_limits("X1 AXIS")

    @property
    def ylimdata(self) -> Union[np.ndarray, da.Array]:
        """Retrieve the y (i.e. X2) grid axis limits."""
        return self._get_coordinate_limits("X2 AXIS")

    @property
    def zlimdata(self) -> Union[np.ndarray, da.Array]:
        """Retrieve the z (i.e. X3) grid axis limits."""
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
        slice_axis: Literal["x","y","z"] = "x",
        **kwargs
    ) -> Tuple[Axes, Union[Line2D, QuadMesh]]:
        """
        Plot 1D, 2D, or 3D data.

        Args:
            ax (Axes, optional): Matplotlib Axes instance.
            dpi (int): Resolution of the plot.
            title (str, optional): Plot title.
            xlabel, ylabel, zlabel (str, optional): Axis labels.
            xlim, ylim, zlim (tuple, optional): Axis limits.
            colormap (str): Colormap name for 2D/3D data.
            show_colorbar (bool): Whether to display the colorbar.
            colorbar_label (str, optional): Label for the colorbar.
            slice_axis (str): Slice axis for 3D data. Must be "x", "y", or "z".
            **kwargs: Additional keyword arguments for the plotting functions.

        Returns:
            Tuple[Axes, Union[Line2D, QuadMesh]]: Matplotlib Axes and plot object.
        """


        num_dimensions = len(self._get_data_shape())
        if not 1 <= num_dimensions <= 3:
            raise NotImplementedError("Plotting is restricted to 1D, 2D, or 3D data.")

        if ax is None:
            fig, ax = plt.subplots(figsize=(8,6), dpi=dpi)
            if num_dimensions ==  3:
                plt.subplots_adjust(bottom=0.2)

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
            if slice_axis not in ["x","y","z"]:
                raise ValueError("Slice axis must be 'x', 'y', or 'z'.")

            ydata = self.ydata.compute() if is_computable(self.ydata) else self.ydata
            ylimdata = self.ylimdata.compute() if is_computable(self.ylimdata) else self.ylimdata
            zdata = self.zdata.compute() if is_computable(self.zdata) else self.zdata
            zlimdata = self.zlimdata.compute() if is_computable(self.zlimdata) else self.zlimdata

            initial_slice = 0
            if slice_axis == "x":
                Y, Z = np.meshgrid(ydata, zdata, indexing="ij")
                mesh = ax.pcolormesh(
                    Y, Z, data[initial_slice,:,:], cmap=colormap, shading="auto", **kwargs
                )
                initial_position_str = f"\nx = {xdata[initial_slice]:.2f}"
                ax.set_xlabel(ylabel if ylabel else "$y$")
                ax.set_ylabel(zlabel if zlabel else "$z$")
                ax.set_xlim(ylim if ylim else ylimdata)
                ax.set_ylim(zlim if zlim else zlimdata)
            elif slice_axis == "y":
                X, Z = np.meshgrid(xdata, zdata, indexing="ij")
                mesh = ax.pcolormesh(
                    X, Z, data[:,initial_slice,:], cmap=colormap, shading="auto", **kwargs
                )
                initial_position_str = f"\ny = {ydata[initial_slice]:.2f}"
                ax.set_xlabel(xlabel if xlabel else "$x$")
                ax.set_ylabel(zlabel if zlabel else "$z$")
                ax.set_xlim(xlim if xlim else xlimdata)
                ax.set_ylim(zlim if zlim else zlimdata)
            else:
                X, Y = np.meshgrid(xdata, ydata, indexing="ij")
                mesh = ax.pcolormesh(
                    X, Y, data[:,:,initial_slice], cmap=colormap, shading="auto", **kwargs
                )
                initial_position_str = f"\nz = {zdata[initial_slice]:.2f}"
                ax.set_xlabel(xlabel if xlabel else "$x$")
                ax.set_ylabel(ylabel if ylabel else "$y$")
                ax.set_xlim(xlim if xlim else xlimdata)
                ax.set_ylim(ylim if ylim else ylimdata)

            ax.set_title(title if title else f"{self._plot_title}{initial_position_str}")
            if show_colorbar:
                cbar = plt.colorbar(mesh, ax=ax)
                cbar.set_label(colorbar_label if colorbar_label else f"{self.name}")

            ax_slider = plt.axes([0.2, 0.05, 0.6, 0.03])
            data_shape = data.shape[{"x": 0, "y": 1, "z": 2}[slice_axis]]
            slider = Slider(ax_slider, f"{slice_axis.capitalize()} axis slice", 0, data_shape-1, valinit=initial_slice, valstep=1)

            def update(val):
                slice_index = int(slider.val)
                if slice_axis == "x":
                    data_slice = data[slice_index,:,:]
                    position_str = f"\nx = {xdata[slice_index]:.2f}"
                elif slice_axis == "y":
                    data_slice = data[:,slice_index,:]
                    position_str = f"\ny = {ydata[slice_index]:.2f}"
                else:
                    data_slice = data[:,:,slice_index]
                    position_str = f"\nz = {zdata[slice_index]:.2f}"

                ax.set_title(title if title else f"{self._plot_title}{position_str}")
                mesh.set_array(data_slice.ravel())
                fig.canvas.draw_idle()

            slider.on_changed(update)
            return ax, mesh


class Field(Data):
    def __init__(self, file_path: str, name: str, timestep: int, lazy: bool, field_type: str):
        super().__init__(file_path, name, timestep, lazy)
        self.type = field_type # The type of field, e.g., "External"
        self._plot_title += f" (type = {self.type})"


class Phase(Data):
    def __init__(self, file_path: str, name: str, timestep: int, lazy: bool, species: Union[int, str]):
        super().__init__(file_path, name, timestep, lazy)
        self.species = species
        self._plot_title += f" (species = {self.species})"


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