import numpy as np 
import os
import re

class DHP:
    def __init__(self, output_path: str):
        self.output_path = output_path
        self.timesteps_dict = {}

        self.fieldname_mapping = {
            "Magnetic": "B",
            "Electric": "E"
        }

        self.traverse_directory()


    def traverse_directory(self):
        file_info = []
        timestep_pattern = re.compile(r"_(\d+)\.h5$")

        for dirpath, _, filenames in os.walk(self.output_path):
            for filename in filenames:
                match = timestep_pattern.search(filename)

                if match:
                    timestep = int(match.group(1))
                    folder_components = os.path.relpath(dirpath, self.output_path).split(os.sep)
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
                        pass


    def timestep(self, ts):
        if ts in self.timesteps_dict:
            return self.timesteps_dict[ts]
        raise ValueError(f"Timestep {ts} not found")


    @property
    def timesteps(self):
        return sorted(list(self.timesteps_dict))


class Field:
    def __init__(self, filename, name, source):
        self.filename = filename
        self.name = name # e.g., "Ex"
        self.source = source # e.g., "External"

    @property
    def data(self):
        # Placeholder for data loading logic
        print(f"Loading data from {self.filename} for type '{self.source}'")


class Phase:
    def __init__(self, filename, phasetype):
        self.filename = filename
        self.phasetype = phasetype

    @property
    def data(self):
        # Placeholder for data loading logic
        print(f"Loading data from {self.filename} for type '{self.phasetype}'")


class Timestep:
    def __init__(self, timestep):
        self.timestep = timestep
        self.fields = {"Total": {}, "External": {}}
        self.phase = {}

    def add_field(self, field):
        if field.source not in self.fields:
            raise ValueError(f"Unknown source: {field.source}")
        self.fields[field.source][field.name] = field

    def add_phase(self, name, phase):
        self.phase[name] = phase

    def __getattr__(self, name):

        def resolve_attr(source="Total"):
            # Check if the name exists in phase. If not, check if it's in fields
            if name in self.phase:
                return self.phase[name]

            # Capitalize source incase user uses all lowercase
            source = source.capitalize()

            # Check if the source exists and contains the name
            field_items = self.fields.get(source, {})
            if name in field_items:
                return field_items[name]

            # Raise an error if not found
            raise AttributeError(f"Field / Phase '{name}' with type '{source}' does not exist for timestep {self.timestep}")

        # Return callable function that allows function argument like "Total" or "External"
        return resolve_attr


def main():
    dhp = DHP("/project/astroplasmas/bricker/dhybridrpy/dhybridrpy/Output")
    print(dhp.timestep(32).Ex().data)
    print(dhp.timesteps)
    print(dhp.timestep(0).Ey("External").filename)

if __name__ == "__main__":
    main()