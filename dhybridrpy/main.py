import numpy as np 
import os
import re
import logging

from collections import defaultdict
from typing import Union, Callable

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Field:
    def __init__(self, filepath: str, name: str, source: str):
        self.filepath = filepath # Absolute path to field file
        self.name = name # e.g., "Ex"
        self.source = source # e.g., "External"

    @property
    def data(self):
        # Placeholder for data loading logic
        return f"Loading data from {self.filepath} for type '{self.source}'"


class Phase:
    def __init__(self, filepath: str, name: str, species: int):
        self.filepath = filepath
        self.name = name
        self.species = species

    @property
    def data(self):
        # Placeholder for data loading logic
        return f"Loading data from {self.filepath} for species '{self.species}'"


class Timestep:
    def __init__(self, timestep):
        self.timestep = timestep
        self.fields = {"Total": {}, "External": {}}
        self.phases = defaultdict(lambda: {})

    def add_field(self, field: Field) -> None:
        if field.source not in self.fields:
            raise ValueError(f"Unknown source: {field.source}")
        self.fields[field.source][field.name] = field

    def add_phase(self, phase: Phase) -> None:
        self.phases[phase.species][phase.name] = phase

    def __getattr__(self, name: str) -> Callable:

        def get_field(source: str) -> Field:
            source = source.capitalize()
            if source not in self.fields or name not in self.fields[source]:
                raise AttributeError(f"Field '{name}' with source '{source}' not found at timestep {self.timestep}")
            return self.fields[source][name]

        def get_phase(species: int) -> Phase:
            if name not in self.phases.get(species, {}):
                raise AttributeError(f"Phase '{name}' for species {species} not found at timestep {self.timestep}")
            return self.phases[species][name]

        def get_attr(arg: Union[str, int] = None) -> Union[Field, Phase]:

            if any(name in phases for phases in self.phases.values()):  # If `name` corresponds to a phase
                return get_phase(species=arg if arg != 1 and arg != None else 1)
            elif any(name in fields for fields in self.fields.values()):  # If `name` is a field
                return get_field(source=arg if arg != "Total" and arg != None else "Total")

            # If `name` is neither a field nor a phase, raise an error
            raise AttributeError(f"Attribute '{name}' does not exist at timestep {self.timestep}")

        # Return callable function that allows function argument like "Total" or "External"
        return get_attr


class DHP:
    def __init__(self, outputpath: str):
        self.outputpath = outputpath
        self.timesteps_dict = {}
        self.fieldname_mapping = {
            "Magnetic": "B",
            "Electric": "E"
        }
        self.traverse_directory()

    def process_file(self, dirpath: str, filename: str, timestep: int) -> None:
        folder_components = os.path.relpath(dirpath, self.outputpath).split(os.sep)
        output_type = folder_components[0]

        if output_type == "Fields":
            self.process_field(dirpath, filename, timestep, folder_components)
        elif output_type == "Phase":
            self.process_phase(dirpath, filename, timestep, folder_components)

    def process_field(self, dirpath: str, filename: str, timestep: int, folder_components: list) -> None:
        category = folder_components[1]
        source = folder_components[-2]
        component = folder_components[-1]

        prefix = self.fieldname_mapping.get(category)
        if not prefix:
            logger.warning(f"Unknown category '{category}'. Skipping {filename}")
            return

        name = f"{prefix}{component}"
        if timestep not in self.timesteps_dict:
            self.timesteps_dict[timestep] = Timestep(timestep)
        field = Field(os.path.join(dirpath, filename), name, source)
        self.timesteps_dict[timestep].add_field(field)

    def process_phase(self, dirpath: str, filename: str, timestep: int, folder_components: list) -> None:
        name = folder_components[-2]
        species = int(re.search(r'\d+', folder_components[-1]).group())
        if timestep not in self.timesteps_dict:
            self.timesteps_dict[timestep] = Timestep(timestep)
        phase = Phase(os.path.join(dirpath, filename), name, species)
        self.timesteps_dict[timestep].add_phase(phase)

    def traverse_directory(self) -> None:
        file_info = []
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


def main():
    dhp = DHP("/project/astroplasmas/bricker/dhybridrpy/dhybridrpy/Output")
    print(dhp.timestep(0).Ez("External").data)
    print(dhp.timestep(32).p1x1(1).data)
    print(dhp.timestep(64).x3x2x1().data)
    print(dhp.timestep(32).EIntensity().data)

if __name__ == "__main__":
    main()