from collections import defaultdict
from typing import Callable
from .data import Field, Phase, Raw

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
            f"origin = {origin}": sorted(fields.keys()) for origin, fields in sorted(self.fields_dict.items())
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
            f"species = {species}": sorted(phases.keys()) for species, phases in self.phases_dict.items()
        }
        return f"Phases at timestep {self.timestep} = {phase_summary}"


class RawContainer:
    def __init__(self, raw_dict: dict, timestep: int):
        self.raw_dict = raw_dict
        self.timestep = timestep

    def __getattr__(self, name: str) -> Callable:
        def get_raw(species: int = 1) -> Raw:
            if name not in self.raw_dict.get(species, {}):
                raise AttributeError(f"Raw file '{name}' for species '{species}' not found at timestep {self.timestep}.")
            return self.raw_dict[species][name]

        return get_raw

    def __repr__(self) -> str:
        raw_summary = {
            f"species = {species}": sorted(raw.keys()) for species, raw in self.raw_dict.items()
        }
        return f"Raw files at timestep {self.timestep} = {raw_summary}"


class Timestep:
    def __init__(self, timestep: int):
        self.timestep = timestep
        self._fields_dict = {"Total": {}, "External": {}, "Self": {}}
        self._phases_dict = defaultdict(lambda: {})
        self._raw_dict = defaultdict(lambda: {})

        # User uses these attributes to dynamically resolve a given field or phase using FieldContainer
        # PhaseContainer, or RawContainer __getattr__ dunder function.
        self.fields = FieldContainer(self._fields_dict, timestep)
        self.phases = PhaseContainer(self._phases_dict, timestep)
        self.raw_files = RawContainer(self._raw_dict, timestep)

    def add_field(self, field: Field) -> None:
        if field.origin not in self._fields_dict:
            raise ValueError(f"Unknown origin: {field.origin}")
        self._fields_dict[field.origin][field.name] = field

    def add_phase(self, phase: Phase) -> None:
        self._phases_dict[phase.species][phase.name] = phase

    def add_raw(self, raw: Raw) -> None:
        self._raw_dict[raw.species][raw.name] = raw

    def __repr__(self) -> str:
        fields_summary = {f"origin = {origin}": list(name.keys()) for origin, name in self._fields_dict.items()}
        phases_summary = {f"species = {species}": list(name.keys()) for species, name in self._phases_dict.items()}
        raw_files_summary = {f"species = {species}": list(name.keys()) for species, name in self._raw_dict.items()}
        return (
            f"Timestep(timestep = {self.timestep}, "
            f"fields = {fields_summary}, "
            f"phases = {phases_summary}, "
            f"raw files = {raw_files_summary})"
        )