from collections import defaultdict
from typing import Callable
from .data import Field, Phase, Raw

class Container:
    def __init__(self, data_dict: dict, timestep: int, container_type: str, key_name: str, default_key_value: int | str):
        self.data_dict = data_dict
        self.timestep = timestep
        self.container_type = container_type.capitalize() if not container_type.isupper() else container_type
        self.key_name = key_name
        self.default_key_value = default_key_value

    def __getattr__(self, data_name: str) -> Callable:
        def get_data(*args, **kwargs) -> Field | Phase | Raw:

            # Ensure there's at most one argument
            if len(args) + len(kwargs) > 1:
                raise TypeError(f"Expected at most one argument.")

            # If the argument is a key value pair, make sure the key is the expected key_name
            if kwargs and self.key_name not in kwargs:
                raise TypeError(f"Argument name must be '{self.key_name}'.")

            # Grab the value if no key is used, otherwise grab the key's value. If kwargs is empty, return the default value.
            key = args[0] if args else kwargs.get(self.key_name, self.default_key_value)

            # If key is a string, make sure it's capitalized
            if isinstance(key, str) and not key.isupper():
                key = key.capitalize()

            # Check if key, data_name (e.g. "Total", "Bx") exist in data_dict at this timestep
            if key not in self.data_dict:
                raise AttributeError(f"{self.container_type} with {self.key_name} '{key}' not found at timestep {self.timestep}.")
            if data_name not in self.data_dict[key]:
                raise AttributeError(f"{self.container_type} '{data_name}' with {self.key_name} '{key}' not found at timestep {self.timestep}.")

            return self.data_dict[key][data_name]

        return get_data

    def __repr__(self) -> str:
        data_summary = {
            f"{self.key_name} = {key}": sorted(data.keys()) for key, data in self.data_dict.items()
        }
        return f"{self.container_type}s at timestep {self.timestep} = {data_summary}"


class FieldContainer(Container):
    def __init__(self, fields_dict: dict, timestep: int):
        super().__init__(
            data_dict=fields_dict,
            timestep=timestep, 
            container_type="Field", 
            key_name="origin", 
            default_key_value="Total"
        )


class PhaseContainer(Container):
    def __init__(self, phases_dict: dict, timestep: int):
        super().__init__(
            data_dict=phases_dict, 
            timestep=timestep, 
            container_type="Phase", 
            key_name="species", 
            default_key_value=1
        )


class RawContainer(Container):
    def __init__(self, raw_dict: dict, timestep: int):
        super().__init__(
            data_dict=raw_dict, 
            timestep=timestep, 
            container_type="Raw file", 
            key_name="species", 
            default_key_value=1
        )


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
        return (
            f"{self.fields}\n"
            f"{self.phases}\n"
            f"{self.raw_files}"
        )