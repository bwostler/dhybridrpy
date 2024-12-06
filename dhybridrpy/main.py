import numpy as np 
import os
import re
import logging

from collections import defaultdict
from typing import Union, Callable

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Field:
    def __init__(self, filepath: str, name: str, origin: str):
        self.filepath = filepath # Absolute path to field file
        self.name = name # e.g., "Ex"
        self.origin = origin # e.g., "External"

    @property
    def data(self):
        # Placeholder for data loading logic
        return f"Loading data from {self.filepath} for origin '{self.origin}'"


class Phase:
    def __init__(self, filepath: str, name: str, species: Union[int, str]):
        self.filepath = filepath
        self.name = name
        self.species = species

    @property
    def data(self):
        # Placeholder for data loading logic
        return f"Loading data from {self.filepath} for species '{self.species}'"


class FieldContainer:
    def __init__(self, fields_dict: dict):
        self.fields_dict = fields_dict

    def __getattr__(self, name: str) -> Callable:
        def get_field(origin: str = "Total") -> Field:
            origin = origin.capitalize()
            if origin not in self.fields_dict or name not in self.fields_dict[origin]:
                raise AttributeError(f"Field '{name}' with origin '{origin}' not found")
            return self.fields_dict[origin][name]

        return get_field


class PhaseContainer:
    def __init__(self, phases_dict: dict):
        self.phases_dict = phases_dict

    def __getattr__(self, name: str) -> Callable:
        def get_phase(species: Union[int, str] = "Total") -> Phase:
            if name not in self.phases_dict.get(species, {}):
                raise AttributeError(f"Phase '{name}' for species '{species}' not found")
            return self.phases_dict[species][name]

        return get_phase


class Timestep:
    def __init__(self, timestep: int):
        self.timestep = timestep
        self.fields_dict = {"Total": {}, "External": {}, "Self": {}, None: {}}
        self.phases_dict = defaultdict(lambda: {})

        # User uses these attributes to dynamically resolve a given field or phase using FieldContainer
        # or PhaseContainer __getattr__() dunder function.
        self.fields = FieldContainer(self.fields_dict)
        self.phases = PhaseContainer(self.phases_dict)

    def add_field(self, field: Field) -> None:
        if field.origin not in self.fields_dict:
            raise ValueError(f"Unknown origin: {field.origin}")
        self.fields_dict[field.origin][field.name] = field

    def add_phase(self, phase: Phase) -> None:
        self.phases_dict[phase.species][phase.name] = phase


class DHP:
    def __init__(self, outputpath: str):
        self.outputpath = outputpath
        self.timesteps_dict = {}
        self.fieldname_mapping = {
            "Magnetic": "B",
            "Electric": "E",
            "FluidVel": "V",
            "CurrentDens": "J"
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


def main():
    dhp = DHP("/project/astroplasmas/bricker/dhybridrpy/dhybridrpy/Output")
    print(dhp.timestep(32).fields.Ez(origin="Total").data)
    print(dhp.timestep(32).phases.x3x2x1(species=1).data)
    print(dhp.timesteps)
    print(dhp.timestep(32).fields.Jx().data)


if __name__ == "__main__":
    main()