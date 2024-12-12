import os
import re
import logging
import numpy as np
import f90nml

from dhybridrpy.containers import Timestep
from dhybridrpy.data import Field, Phase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InputFileParser:
    def __init__(self, input_file: str):
        self.input_file = input_file
        self.input_dict = self._parse_input_file()

    def _parse_input_file(self) -> dict:
        """
        Parses the input file and returns its content as a subclass of dictionary.
        Temporary files are managed and removed automatically.
        """
        tmp_input_file = f"{self.input_file}.tmp"
        try:
            self._create_nml_input_file(tmp_input_file)
            return f90nml.read(tmp_input_file)
        finally:
            # Ensure the temporary file is cleaned up
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
    def __init__(self, input_file: str, output_path: str):
        self.input_file = input_file
        self.output_path = output_path
        self._timesteps_dict = {}
        self._field_mapping = {
            "Magnetic": "B",
            "Electric": "E",
            "FluidVel": "V",
            "CurrentDens": "J"
        }
        self._traverse_directory()
        self.inputs = InputFileParser(input_file).input_dict

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
        field = Field(os.path.join(dirpath, filename), name, timestep, origin)
        self._timesteps_dict[timestep].add_field(field)

    def _process_phase(self, dirpath: str, filename: str, timestep: int, folder_components: list) -> None:
        name = folder_components[-2]
        species_str = folder_components[-1]
        species = int(re.search(r'\d+', species_str).group()) if species_str != "Total" else species_str
        if timestep not in self._timesteps_dict:
            self._timesteps_dict[timestep] = Timestep(timestep)
        phase = Phase(os.path.join(dirpath, filename), name, timestep, species)
        self._timesteps_dict[timestep].add_phase(phase)

    def _traverse_directory(self) -> None:
        timestep_pattern = re.compile(r"_(\d+)\.h5$")
        for dirpath, _, filenames in os.walk(self.output_path):
            for filename in filenames:
                match = timestep_pattern.search(filename)
                if match:
                    timestep = int(match.group(1))
                    self._process_file(dirpath, filename, timestep)

    def timestep(self, ts: int) -> Timestep:
        if ts in self._timesteps_dict:
            return self._timesteps_dict[ts]
        raise ValueError(f"Timestep {ts} not found")

    @property
    def timesteps(self) -> np.array:
        return np.sort(list(self._timesteps_dict))