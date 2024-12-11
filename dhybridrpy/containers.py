from collections import defaultdict
from typing import Callable, Union
from dhybridrpy.data import Field, Phase

class FieldContainer:
    def __init__(self, fields_dict: dict):
        self.fields_dict = fields_dict

    def __getattr__(self, name: str) -> Callable:
        def get_field(origin: str = "Total") -> Field:
            origin = origin.capitalize()
            if origin not in self.fields_dict or name not in self.fields_dict[origin]:
                raise AttributeError(f"Field '{name}' with origin '{origin}' not found at this timestep.")
            return self.fields_dict[origin][name]

        return get_field


class PhaseContainer:
    def __init__(self, phases_dict: dict):
        self.phases_dict = phases_dict

    def __getattr__(self, name: str) -> Callable:
        def get_phase(species: Union[int, str] = 1) -> Phase:
            if name not in self.phases_dict.get(species, {}):
                raise AttributeError(f"Phase '{name}' for species '{species}' not found at this timestep.")
            return self.phases_dict[species][name]

        return get_phase


class Timestep:
    def __init__(self, timestep: int):
        self.timestep = timestep
        self.fields_dict = {"Total": {}, "External": {}, "Self": {}}
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