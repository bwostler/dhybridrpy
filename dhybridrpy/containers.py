from collections import defaultdict
from typing import Callable
from .data import Field, Phase

class FieldContainer:
    def __init__(self, fields_dict: dict, timestep: int):
        self.fields_dict = fields_dict
        self.timestep = timestep

    def __getattr__(self, name: str) -> Callable:
        def get_field(origin: str = "Total") -> Field:
            origin = origin.capitalize()
            if origin not in self.fields_dict or name not in self.fields_dict[origin]:
                raise AttributeError(f"Field '{name}' with origin '{origin}' not found at timestep {self.timestep}.")
            return self.fields_dict[origin][name]

        return get_field

    def __repr__(self) -> str:
        field_summary = {
            f"origin = {origin}": list(fields.keys()) for origin, fields in self.fields_dict.items()
        }
        return f"Fields at timestep {self.timestep} = {field_summary}"


class PhaseContainer:
    def __init__(self, phases_dict: dict, timestep: int):
        self.phases_dict = phases_dict
        self.timestep = timestep

    def __getattr__(self, name: str) -> Callable:
        def get_phase(species: int | str = 1) -> Phase:
            if name not in self.phases_dict.get(species, {}):
                raise AttributeError(f"Phase '{name}' for species '{species}' not found at timestep {self.timestep}.")
            return self.phases_dict[species][name]

        return get_phase

    def __repr__(self) -> str:
        phase_summary = {
            f"species = {species}": list(phases.keys()) for species, phases in self.phases_dict.items()
        }
        return f"Phases at timestep {self.timestep} = {phase_summary}"


class Timestep:
    def __init__(self, timestep: int):
        self.timestep = timestep
        self.fields_dict = {"Total": {}, "External": {}, "Self": {}}
        self.phases_dict = defaultdict(lambda: {})

        # User uses these attributes to dynamically resolve a given field or phase using FieldContainer
        # or PhaseContainer __getattr__ dunder function.
        self.fields = FieldContainer(self.fields_dict, timestep)
        self.phases = PhaseContainer(self.phases_dict, timestep)

    def add_field(self, field: Field) -> None:
        if field.origin not in self.fields_dict:
            raise ValueError(f"Unknown origin: {field.origin}")
        self.fields_dict[field.origin][field.name] = field

    def add_phase(self, phase: Phase) -> None:
        self.phases_dict[phase.species][phase.name] = phase

    def __repr__(self) -> str:
        fields_repr = {k: list(v.keys()) for k, v in self.fields_dict.items()}
        phases_repr = {k: list(v.keys()) for k, v in self.phases_dict.items()}
        return (
            f"Timestep(timestep={self.timestep}, "
            f"fields={fields_repr}, "
            f"phases={phases_repr})"
        )