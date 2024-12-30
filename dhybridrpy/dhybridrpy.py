import os
import re
import logging
import numpy as np
import f90nml

from .containers import Timestep
from .data import Field, Phase
from f90nml import Namelist
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InputFileParser:
    def __init__(self, input_file: str):
        self.input_file = input_file
        self.input_dict = self._parse_input_file()

    def _parse_input_file(self) -> Namelist:
        """
        Parses the input file and returns its content as a subclass of dictionary.
        Temporary files are managed and removed automatically.
        """
        tmp_input_file = f"{self.input_file}.tmp"
        try:
            self._create_nml_input_file(tmp_input_file)
            return f90nml.read(tmp_input_file)
        except Exception as e:
            logger.error(f"Failed to parse input file: {e}")
            raise
        finally:
            if os.path.exists(tmp_input_file):
                os.remove(tmp_input_file)

    def _create_nml_input_file(self, output_file: str) -> None:
        """
        Converts the input file content to a Fortran namelist format
        and writes it to the specified output filename.
        """
        with open(self.input_file, 'r') as infile:
            content = infile.read()

        # Regular expression to match sections with curly braces
        section_pattern = re.compile(r'(\w+)\s*\{([^}]*)\}', re.DOTALL)

        # Generate namelist content
        namelist_content = []
        for match in section_pattern.finditer(content):
            section_name, parameters = match.group(1), match.group(2).strip()

            # Begin the namelist section
            namelist_content.append(f"&{section_name}")
            namelist_content.extend(self._process_parameters(parameters))
            namelist_content.append("/")  # End the namelist section

        # Write the processed content to the output file
        with open(output_file, 'w') as outfile:
            outfile.write("\n".join(namelist_content))

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


class Dhybridrpy:

    _field_mapping = {
        "Magnetic": "B",
        "Electric": "E",
        "CurrentDens": "J"
    }
    _phase_mapping = {
        "FluidVel": "V"
    }

    def __init__(self, input_file: str, output_path: str, lazy: bool = False):
        self.input_file = input_file
        self.output_path = output_path
        self.lazy = lazy
        self._timesteps_dict = {}
        self._sorted_timesteps = None
        self._validate_paths()
        self._traverse_directory()
        self.inputs = InputFileParser(input_file).input_dict

    def _validate_paths(self):
        if not os.path.exists(self.input_file):
            raise FileNotFoundError(f"Input file {self.input_file} does not exist")
        if not os.path.isdir(self.output_path):
            raise NotADirectoryError(f"Output path {self.output_path} is not a directory")

    def _process_file(self, dirpath: str, filename: str, timestep: int) -> None:
        folder_components = os.path.relpath(dirpath, self.output_path).split(os.sep)
        output_type = folder_components[0]

        if output_type == "Fields":
            self._process_field(dirpath, filename, timestep, folder_components)
        elif output_type == "Phase":
            self._process_phase(dirpath, filename, timestep, folder_components)

    def _process_field(self, dirpath: str, filename: str, timestep: int, folder_components: list) -> None:
        category = folder_components[1]
        if category == "CurrentDens":
            folder_components.insert(2, "Total")
        origin = folder_components[-2]
        component = folder_components[-1]

        prefix = self._field_mapping.get(category)
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

        # Manage bulk velocity and pressure special cases
        if name == "FluidVel":
            species_str = folder_components[-2]
            component = folder_components[-1]
            prefix = self._phase_mapping.get(name)
            if not prefix:
                logger.warning(f"Unknown name '{name}'. Skipping {filename}")
                return
            name = f"{prefix}{component}"
        else:
            species_str = folder_components[-1]

        if name == "x3x2x1" and "pres" in filename:
            name = "P"
        
        species = int(re.search(r'\d+', species_str).group()) if species_str != "Total" else species_str
        if timestep not in self._timesteps_dict:
            self._timesteps_dict[timestep] = Timestep(timestep)
        phase = Phase(os.path.join(dirpath, filename), name, timestep, self.lazy, species)
        self._timesteps_dict[timestep].add_phase(phase)

    def _traverse_directory(self) -> None:
        timestep_pattern = re.compile(r"_(\d+)\.h5$")
        file_params = []

        for dirpath, _, filenames in os.walk(self.output_path):
            for filename in filenames:
                match = timestep_pattern.search(filename)
                if match:
                    timestep = int(match.group(1))
                    file_params.append((dirpath, filename, timestep))

        # for loop with "pass" below is there to allow errors in individual threads 
        # to properly propagate up to the main thread instead of being suppressed. 
        with ThreadPoolExecutor() as executor:
            for _ in executor.map(lambda params: self._process_file(*params), file_params):
                pass

    def timestep(self, ts: int) -> Timestep:
        if ts in self._timesteps_dict:
            return self._timesteps_dict[ts]
        raise ValueError(f"Timestep {ts} not found")

    def timesteps(self, exclude_zero: bool = True) -> np.ndarray:
        if self._sorted_timesteps is None:
            self._sorted_timesteps = np.sort(list(self._timesteps_dict))
        if exclude_zero and len(self._sorted_timesteps) > 0 and self._sorted_timesteps[0] == 0:
            return self._sorted_timesteps[1:]
        return self._sorted_timesteps