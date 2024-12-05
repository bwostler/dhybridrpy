import numpy as np 
import os
import re

from collections import defaultdict
from typing import Union, Callable

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
        print(f"Loading data from {self.filepath} for species '{self.species}'")


class DHP:
    def __init__(self, outputpath: str):
        self.outputpath = outputpath
        self.timesteps_dict = {}

        self.fieldname_mapping = {
            "Magnetic": "B",
            "Electric": "E"
        }

        self.traverse_directory()


    def traverse_directory(self):
        file_info = []
        timestep_pattern = re.compile(r"_(\d+)\.h5$")

        for dirpath, _, filenames in os.walk(self.outputpath):
            for filename in filenames:
                match = timestep_pattern.search(filename)

                if match:
                    timestep = int(match.group(1))
                    folder_components = os.path.relpath(dirpath, self.outputpath).split(os.sep)
                    output_type = folder_components[0]
                    
                    # Handle files corresponding to fields
                    if output_type == "Fields":
                        category = folder_components[1] # e.g., 'Magnetic' or 'Electric'
                        source = folder_components[-2] # e.g., 'Total' or 'External'
                        component = folder_components[-1] # e.g., 'x', 'y', 'z'

                        try:
                            prefix = self.fieldname_mapping[category]
                        except KeyError:
                            print(f"Warning: Key '{category}' has no known mapping in field name mapping dictionary. Continuing without renaming")
                            continue

                        name = f"{prefix}{component}"

                        # Ensure the timestep exists
                        if timestep not in self.timesteps_dict:
                            self.timesteps_dict[timestep] = Timestep(timestep)
                        
                        # Add the field to the timestep
                        field = Field(os.path.join(dirpath, filename), name, source)
                        self.timesteps_dict[timestep].add_field(field)

                    elif output_type == "Phase":
                        
                        name = folder_components[-2]

                        # Extract integer characterizing species type in a general way
                        species_match = re.search(r'\d+', folder_components[-1])
                        if species_match:
                            species = int(species_match.group())
                        
                        # Ensure the timestep exists
                        if timestep not in self.timesteps_dict:
                            self.timesteps_dict[timestep] = Timestep(timestep)

                        phase = Phase(os.path.join(dirpath, filename), name, species)
                        self.timesteps_dict[timestep].add_phase(phase)
                        


    def timestep(self, ts: int) -> Union[Field, Phase]:
        if ts in self.timesteps_dict:
            return self.timesteps_dict[ts]
        raise ValueError(f"Timestep {ts} not found")


    @property
    def timesteps(self) -> np.array:
        return np.sort(list(self.timesteps_dict))


class Timestep:
    def __init__(self, timestep):
        self.timestep = timestep
        self.fields = {"Total": {}, "External": {}}
        self.phases = defaultdict(lambda: {})

    def add_field(self, field: Field):
        if field.source not in self.fields:
            raise ValueError(f"Unknown source: {field.source}")
        self.fields[field.source][field.name] = field

    def add_phase(self, phase: Phase):
        self.phases[phase.species][phase.name] = phase

    def __getattr__(self, name: str) -> Callable:

        def resolve_field(source: str) -> Field:

            # Capitalize source incase user uses all lowercase
            source = source.capitalize()

            # Check if the source exists and contains the name
            field_items = self.fields.get(source, {})
            if name in field_items:
                return field_items[name]

            # Raise an error if not found
            raise AttributeError(f"Field '{name}' for type '{source}' does not exist at timestep {self.timestep}")

        def resolve_phase(species: int) -> Phase:
            try:
                return self.phases[species][name]
            except KeyError:
                raise AttributeError(f"Phase '{name}' for species {species} does not exist at timestep {self.timestep}")

        def resolve_attr(arg: Union[str, int] = None) -> Union[Field, Phase]:

            if any(name in phases for phases in self.phases.values()):  # If `name` corresponds to a phase
                return resolve_phase(species=arg if arg != 1 and arg != None else 1)
            elif any(name in fields for fields in self.fields.values()):  # If `name` is a field
                return resolve_field(source=arg if arg != "Total" and arg != None else "Total")

            # If `name` is neither a field nor a phase, raise an error
            raise AttributeError(f"Attribute '{name}' does not exist at timestep {self.timestep}")

        # Return callable function that allows function argument like "Total" or "External"
        return resolve_attr


def main():
    dhp = DHP("/project/astroplasmas/bricker/dhybridrpy/dhybridrpy/Output")
    print(dhp.timestep(0).Ez("External").data)
    print(dhp.timestep(32).p1x1(1).data)

if __name__ == "__main__":
    main()