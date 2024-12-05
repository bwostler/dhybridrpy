import numpy as np 
import os
import re

class DHP:
    def __init__(self, output_path: str):
        self.output_path = output_path
        self._timesteps = {}

        self.field_name_mapping = {
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
                        field_category = folder_components[1] # e.g., 'Magnetic' or 'Electric'
                        field_type = folder_components[-2] # e.g., 'Total' or 'External'
                        component = folder_components[-1] # e.g., 'x', 'y', 'z'

                        try:
                            prefix = self.field_name_mapping[field_category]
                        except KeyError:
                            print(f"Warning: Key '{field_category}' has no known mapping in field name mapping dictionary. Continuing without renaming")
                            continue

                        field_name = f"{prefix}{component}"

                        # Ensure the timestep exists
                        if timestep not in self._timesteps:
                            self._timesteps[timestep] = Timestep(timestep)
                        
                        # Add the field to the timestep
                        field = Field(os.path.join(dirpath, filename), field_type)
                        self._timesteps[timestep].add_field(field_name, field)
                    elif output_type == "Phase":
                        pass


    def timestep(self, ts):
        if ts in self._timesteps:
            return self._timesteps[ts]
        raise ValueError(f"Timestep {ts} not found")


    @property
    def timesteps(self):
        return sorted(list(self._timesteps))

        

class Field:
    def __init__(self, filename, field_type):
        self.filename = filename
        self.field_type = field_type

    @property
    def data(self):
        # Placeholder for data loading logic
        print(f"Loading data from {self.filename} for type '{self.field_type}'")


class Phase:
    def __init__(self, filename, phase_type):
        self.filename = filename
        self.phase_type = phase_type

    @property
    def data(self):
        # Placeholder for data loading logic
        print(f"Loading data from {self.filename} for type '{self.phase_type}'")


class Timestep:
    def __init__(self, timestep):
        self.timestep = timestep
        self.fields = {"Total": {}, "External": {}}
        self.phase = {}

    def add_field(self, name, field):
        if field.field_type not in self.fields:
            raise ValueError(f"Unknown field_type: {field.field_type}")
        self.fields[field.field_type][name] = field

    def add_phase(self, name, phase):
        self.phase[name] = phase

    def __getattr__(self, name):

        def resolve_field(field_type="Total"):
            # Check if the name exists in phase
            if name in self.phase:
                return self.phase[name]

            # Capitalize field_type incase user uses all lowercase
            field_type = field_type.capitalize()

            # Check if the field_type exists and contains the name
            field_group = self.fields.get(field_type, {})
            if name in field_group:
                return field_group[name]

            # Raise an error if not found
            raise AttributeError(f"Field '{name}' with type '{field_type}' does not exist for timestep {self.timestep}")

        # Return callable function that allows function argument like "Total" or "External"
        return resolve_field


def main():
    dhp = DHP("/project/astroplasmas/bricker/dhybridrpy/dhybridrpy/Output")
    print(dhp.timestep(1).Ex().data)
    print(dhp.timesteps)

if __name__ == "__main__":
    main()