import os
import re
import logging
import numpy as np
import f90nml

from containers import Timestep
from data import Field, Phase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Input:
    def __init__(self, inputfile: str):
        self.inputfile = inputfile
        outputfile = f"{self.inputfile}.tmp"
        self.convert_inputfile_format(outputfile)
        self.input_dict = f90nml.read(outputfile)
        os.remove(outputfile)

    def convert_inputfile_format(self, outputfile: str) -> None:

        with open(self.inputfile, 'r') as infile:
            content = infile.read()

        # Pattern to match sections with curly braces
        pattern = re.compile(r'(\w+)\s*\{([^}]*)\}', re.DOTALL)

        # Create output content
        namelist_output = []

        for match in pattern.finditer(content):
            section_name = match.group(1)
            parameters = match.group(2).strip()

            # Start the namelist
            namelist_output.append(f"&{section_name}")
            
            # Process parameters
            for line in parameters.splitlines():
                line = line.strip()
                if line.startswith("!") or not line:
                    # Retain comments and skip empty lines
                    namelist_output.append(line)
                else:
                    # Remove trailing commas and add parameters
                    namelist_output.append(line.rstrip(','))

            # End the namelist
            namelist_output.append("/\n")

        # Write to output file
        with open(outputfile, 'w') as outfile:
            outfile.write("\n".join(namelist_output))


class dhybridrpy:
    def __init__(self, outputpath: str, inputfile: str):
        self.outputpath = outputpath
        self.inputfile = inputfile
        self.timesteps_dict = {}
        self.fieldname_mapping = {
            "Magnetic": "B",
            "Electric": "E",
            "FluidVel": "V",
            "CurrentDens": "J"
        }
        self.traverse_directory()
        self.inputs = Input(inputfile).input_dict

    def process_file(self, dirpath: str, filename: str, timestep: int) -> None:
        folder_components = os.path.relpath(dirpath, self.outputpath).split(os.sep)
        output_type = folder_components[0]

        if output_type == "Fields":
            self.process_field(dirpath, filename, timestep, folder_components)
        elif output_type == "Phase":
            self.process_phase(dirpath, filename, timestep, folder_components)

    def process_field(self, dirpath: str, filename: str, timestep: int, folder_components: list) -> None:
        category = folder_components[1]
        if category == "CurrentDens":
            folder_components.insert(2, "Total")
        origin = folder_components[-2]
        component = folder_components[-1]

        prefix = self.fieldname_mapping.get(category)
        if not prefix:
            logger.warning(f"Unknown category '{category}'. Skipping {filename}")
            return

        name = f"{prefix}{component}"
        if timestep not in self.timesteps_dict:
            self.timesteps_dict[timestep] = Timestep(timestep)
        field = Field(os.path.join(dirpath, filename), name, origin)
        self.timesteps_dict[timestep].add_field(field)

    def process_phase(self, dirpath: str, filename: str, timestep: int, folder_components: list) -> None:
        name = folder_components[-2]
        species_str = folder_components[-1]
        species = int(re.search(r'\d+', species_str).group()) if species_str != "Total" else species_str
        if timestep not in self.timesteps_dict:
            self.timesteps_dict[timestep] = Timestep(timestep)
        phase = Phase(os.path.join(dirpath, filename), name, species)
        self.timesteps_dict[timestep].add_phase(phase)

    def traverse_directory(self) -> None:
        timestep_pattern = re.compile(r"_(\d+)\.h5$")
        for dirpath, _, filenames in os.walk(self.outputpath):
            for filename in filenames:
                match = timestep_pattern.search(filename)
                if match:
                    timestep = int(match.group(1))
                    self.process_file(dirpath, filename, timestep)

    def timestep(self, ts: int) -> Timestep:
        if ts in self.timesteps_dict:
            return self.timesteps_dict[ts]
        raise ValueError(f"Timestep {ts} not found")

    @property
    def timesteps(self) -> np.array:
        return np.sort(list(self.timesteps_dict))