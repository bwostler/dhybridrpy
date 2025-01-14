import os
import re
import logging
import numpy as np
import f90nml
import io

from .containers import Timestep
from .data import Field, Phase, Raw
from f90nml import Namelist

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
        origin = folder_components[-2]
        component = folder_components[-1]
        if component in self._COMPONENT_MAPPING:
            component = self._COMPONENT_MAPPING[component]

        prefix = self._FIELD_MAPPING.get(category)
        if not prefix:
            logger.warning(f"Unknown category '{category}'. Skipping {filename}")
            return

        name = f"{prefix}{component}"
        if timestep not in self._timesteps_dict:
            self._timesteps_dict[timestep] = Timestep(timestep)
        field = Field(os.path.join(dirpath, filename), name, timestep, self.lazy, origin)
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