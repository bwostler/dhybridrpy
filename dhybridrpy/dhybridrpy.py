import os
import re
import logging
import numpy as np
import f90nml
import io
import matplotlib.pyplot as plt
import matplotlib.animation as animation

from .containers import Timestep
from .data import Field, Phase, Raw
from f90nml import Namelist
from matplotlib.widgets import Slider, Button
from matplotlib.collections import QuadMesh
from matplotlib.axes import Axes
from matplotlib.backend_bases import KeyEvent
from typing import Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InputFileParser:
    def __init__(self, input_file: str):
        self.input_file = input_file
        self.input_dict = self._parse_input_file()

    def _parse_input_file(self) -> Namelist:
        """
        Parses the input file and returns its content as a subclass of dictionary.
        """
        try:
            nml_content = self._create_nml_input_str()
            return f90nml.read(io.StringIO(nml_content))
        except Exception as e:
            logger.error(f"Failed to parse input file: {e}")
            raise

    def _create_nml_input_str(self) -> str:
        """
        Converts the input file content to a Fortran namelist format.
        """
        with open(self.input_file, 'r') as infile:
            content = infile.read()

        # Regular expression to match sections with curly braces
        SECTION_PATTERN = re.compile(r'(\w+)\s*\{([^}]*)\}', re.DOTALL)

        # Generate namelist content
        namelist_content = []
        for match in SECTION_PATTERN.finditer(content):
            section_name, parameters = match.group(1), match.group(2).strip()

            # Begin the namelist section
            namelist_content.append(f"&{section_name}")
            namelist_content.extend(self._process_parameters(parameters))
            namelist_content.append("/")  # End the namelist section

        return "\n".join(namelist_content)

    def _process_parameters(self, parameters: str) -> list:
        """
        Processes the parameters within a section, retaining comments
        and ensuring valid namelist syntax.
        """
        processed_lines = []
        for line in parameters.splitlines():
            line = line.strip()
            if line.startswith("!") or not line:
                # Retain comments or skip empty lines
                processed_lines.append(line)
            else:
                # Ensure proper formatting by removing trailing commas
                processed_lines.append(line.rstrip(','))
        return processed_lines


class DHybridrpy:
    """
    Class for processing dHybridR input and output files.

    Args:
        input_file (str): Path to the dHybridR input file.
        output_folder (str): Path to the dHybridR output folder.
        lazy (bool, optional): Enables lazy loading of data via the dask library.
        exclude_timestep_zero (bool, optional): Excludes the zeroth timestep, if present, from the list of timesteps.
    """

    _FIELD_MAPPING = {
        "Magnetic": "B",
        "Electric": "E",
        "CurrentDens": "J"
    }
    _PHASE_MAPPING = {
        "FluidVel": "V",
        "PressureTen": "P"
    }
    _COMPONENT_MAPPING = {
        "Intensity": "magnitude"
    }
    _SPECIES_PATTERN = re.compile(r'\d+')

    def __init__(self, input_file: str, output_folder: str, lazy: bool = False, exclude_timestep_zero: bool = True):
        self.input_file = input_file
        self.output_folder = output_folder
        self.lazy = lazy
        self.exclude_timestep_zero = exclude_timestep_zero
        self._FIELD_NAMES = []
        self._PHASE_NAMES = []
        self._timesteps_dict = {}
        self._sorted_timesteps = None
        self._validate_paths()
        self._traverse_directory()
        self.inputs = InputFileParser(input_file).input_dict

    def _validate_paths(self):
        if not os.path.exists(self.input_file):
            raise FileNotFoundError(f"Input file {self.input_file} does not exist.")
        if not os.path.isdir(self.output_folder):
            raise NotADirectoryError(f"Output folder {self.output_folder} is not a directory.")

    def _process_file(self, dirpath: str, filename: str, timestep: int) -> None:
        folder_components = os.path.relpath(dirpath, self.output_folder).split(os.sep)
        output_type = folder_components[0]

        if output_type == "Fields":
            self._process_field(dirpath, filename, timestep, folder_components)
        elif output_type == "Phase":
            self._process_phase(dirpath, filename, timestep, folder_components)
        elif output_type == "Raw":
            self._process_raw(dirpath, filename, timestep, folder_components)
        else:
            logger.warning(f"Unknown output type '{output_type}' for {filename}. File not processed.")

    def _process_field(self, dirpath: str, filename: str, timestep: int, folder_components: list) -> None:
        category = folder_components[1]
        if category == "CurrentDens":
            folder_components.insert(2, "Total")
        field_type = folder_components[-2]
        component = folder_components[-1]
        if component in self._COMPONENT_MAPPING:
            component = self._COMPONENT_MAPPING[component]

        prefix = self._FIELD_MAPPING.get(category)
        if not prefix:
            logger.warning(f"Unknown category '{category}'. Skipping {filename}")
            return

        name = f"{prefix}{component}"
        self._FIELD_NAMES.append(name)
        if timestep not in self._timesteps_dict:
            self._timesteps_dict[timestep] = Timestep(timestep)
        field = Field(os.path.join(dirpath, filename), name, timestep, self.lazy, field_type)
        self._timesteps_dict[timestep].add_field(field)

    def _process_phase(self, dirpath: str, filename: str, timestep: int, folder_components: list) -> None:
        name = folder_components[1]
        
        # Manage bulk velocity, pressure tensor, and scalar pressure special cases
        if name == "FluidVel" or name == "PressureTen":
            species_str = folder_components[-2]
            component = folder_components[-1]
            if component in self._COMPONENT_MAPPING:
                component = self._COMPONENT_MAPPING[component]
            prefix = self._PHASE_MAPPING.get(name)
            if not prefix:
                logger.warning(f"Unknown name '{name}'. Skipping {filename}")
                return
            name = f"{prefix}{component}"
        else:
            species_str = folder_components[-1]

        if name == "x3x2x1" and "pres" in filename:
            name = "P"
        
        self._PHASE_NAMES.append(name)
        species = int(self._SPECIES_PATTERN.search(species_str).group()) if species_str != "Total" else species_str
        if timestep not in self._timesteps_dict:
            self._timesteps_dict[timestep] = Timestep(timestep)
        phase = Phase(os.path.join(dirpath, filename), name, timestep, self.lazy, species)
        self._timesteps_dict[timestep].add_phase(phase)

    def _process_raw(self, dirpath: str, filename: str, timestep: int, folder_components: list) -> None:
        name = "raw"
        species_str = folder_components[-1]
        species = int(self._SPECIES_PATTERN.search(species_str).group())
        if timestep not in self._timesteps_dict:
            self._timesteps_dict[timestep] = Timestep(timestep)
        raw = Raw(os.path.join(dirpath, filename), name, timestep, self.lazy, species)
        self._timesteps_dict[timestep].add_raw(raw)

    def _traverse_directory(self) -> None:
        TIMESTEP_PATTERN = re.compile(r"_(\d+)\.h5$")
        for dirpath, _, filenames in os.walk(self.output_folder):
            for filename in filenames:
                match = TIMESTEP_PATTERN.search(filename)
                if match:
                    timestep = int(match.group(1))
                    self._process_file(dirpath, filename, timestep)

    def timestep(self, ts: int) -> Timestep:
        """Access field, phase, and raw file information at a given timestep."""
        if ts in self._timesteps_dict:
            return self._timesteps_dict[ts]
        raise ValueError(f"Timestep {ts} not found.")

    def timestep_index(self, index: int) -> Timestep:
        """Access field, phase, and raw file information at a given timestep index."""
        timesteps = self.timesteps()
        num_timesteps = len(timesteps)
        if -num_timesteps <= index < num_timesteps:
            return self.timestep(timesteps[index])
        raise IndexError(f"Index {index} is out of range. Valid range: {-num_timesteps} to {num_timesteps-1}.")

    def timesteps(self) -> np.ndarray:
        """Retrieve an array of the timesteps."""
        if self._sorted_timesteps is None:
            self._sorted_timesteps = np.sort(list(self._timesteps_dict))
        if self.exclude_timestep_zero and len(self._sorted_timesteps) > 0 and self._sorted_timesteps[0] == 0:
            return self._sorted_timesteps[1:]
        return self._sorted_timesteps

    def animate(
        self, 
        data_name: str, 
        timesteps: Optional[np.ndarray] = None, 
        animation_interval: int = 200,
        **kwargs
    ) -> None:

        cache = {}

        if timesteps is None:
            timesteps = self.timesteps()

        num_timesteps = len(timesteps)
        state = {
            "current_frame": 0,
            "is_paused": True
        }

        fig, ax = plt.subplots(figsize=(8,6))
        plt.subplots_adjust(bottom=0.25)

        if data_name in self._FIELD_NAMES:
            container_name = "fields"
        elif data_name in self._PHASE_NAMES:
            container_name = "phases"
        else:
            raise ValueError(f"Name '{data_name}' is not a known field or phase.")

        initial_timestep = timesteps[state["current_frame"]]
        data_obj = getattr(getattr(self.timestep(initial_timestep), container_name), data_name)(**kwargs)
        cache[state["current_frame"]] = data_obj.data, data_obj._plot_title

        num_dimensions = len(data_obj._get_data_shape())
        if num_dimensions != 2:
            raise NotImplementedError("Animations are restricted to 2D data.")

        ax, mesh = data_obj.plot(ax=ax)

        def update_plot(frame: int, ax, mesh) -> None:
            state["current_frame"] = frame

            if frame in cache:
                data, plot_title = cache[frame]
            else:
                ts = timesteps[frame]
                data_obj = getattr(getattr(self.timestep(ts), container_name), data_name)(**kwargs)
                data, plot_title = data_obj.data, data_obj._plot_title
                cache[frame] = data, plot_title

            mesh.set_array(data.ravel())
            ax.set_title(plot_title)
            fig.canvas.draw_idle()

        def animate_frame(i: int) -> Tuple:
            if not state["is_paused"]:
                new_frame = (state["current_frame"] + 1) % num_timesteps
                slider.set_val(new_frame)
            return (mesh,)
        
        ax_slider = plt.axes([0.2, 0.1, 0.6, 0.03])
        slider = Slider(
            ax_slider,
            "Frame",
            0,
            num_timesteps-1,
            valinit=state["current_frame"],
            valstep=1,
            valfmt="%d"
        )
        slider.on_changed(lambda val: update_plot(val, ax, mesh))

        ax_button = plt.axes([0.05, 0.95, 0.1, 0.04])
        play_pause_button = Button(ax_button, "Play" if state["is_paused"] else "Pause")

        def update_button_text():
            if state["is_paused"]:
                play_pause_button.label.set_text("Play")
            else:
                play_pause_button.label.set_text("Pause")
            fig.canvas.draw_idle()

        def on_button_clicked(event):
            state["is_paused"] = not state["is_paused"]
            update_button_text()

        play_pause_button.on_clicked(on_button_clicked)

        def on_key(event) -> None:
            if event.key == " ":
                state["is_paused"] = not state["is_paused"]
                update_button_text()
            elif event.key == "right":
                new_frame = (state["current_frame"] + 1) % num_timesteps
                slider.set_val(new_frame)
            elif event.key == "left":
                new_frame = (state["current_frame"] - 1) % num_timesteps
                slider.set_val(new_frame)

        fig.canvas.mpl_connect("key_press_event", on_key)

        ani = animation.FuncAnimation(fig, animate_frame, interval=animation_interval, blit=True)
        plt.show()