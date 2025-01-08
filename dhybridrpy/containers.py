from collections import defaultdict
from typing import Callable
from .data import Field, Phase, Raw
from typing import Union

class Container:
    def __init__(self, data_dict: dict, timestep: int, container_type: str, kwarg: str, default_kwarg_value: Union[int, str]):
        self.data_dict = data_dict
        self.timestep = timestep
        self.container_type = container_type.capitalize() if not container_type.isupper() else container_type
        self.kwarg = kwarg
        self.default_kwarg_value = default_kwarg_value

    def __getattr__(self, data_name: str) -> Callable:
        def get_data(*args, **kwargs) -> Union[Field, Phase, Raw]:

            # Ensure there's at most one argument
            if len(args) + len(kwargs) > 1:
                raise TypeError(f"Expected at most one argument.")

            # If the argument is a key value pair, make sure the key is the expected kwarg
            if kwargs and self.kwarg not in kwargs:
                raise TypeError(f"Argument name '{next(iter(kwargs))}' must be '{self.kwarg}'.")

            # Grab the value if no key is used, otherwise grab the key's value. If kwargs is empty, return the default value.
            data_key = args[0] if args else kwargs.get(self.kwarg, self.default_kwarg_value)

            # If data_key is a string, make sure it's capitalized
            if isinstance(data_key, str) and not data_key.isupper():
                data_key = data_key.capitalize()

            # Check if data_key, data_name (e.g. "Total", "Bx") exist in data_dict at this timestep
            if data_key not in self.data_dict:
                raise AttributeError(f"{self.container_type} with {self.kwarg} '{data_key}' not found at timestep {self.timestep}.")
            if data_name not in self.data_dict[data_key]:
                raise AttributeError(f"{self.container_type} '{data_name}' with {self.kwarg} '{data_key}' not found at timestep {self.timestep}.")

            return self.data_dict[data_key][data_name]

        return get_data

    def __repr__(self) -> str:
        data_summary = {
            f"{self.kwarg} = {key}": sorted(value.keys()) for key, value in self.data_dict.items()
        }
        return f"{self.container_type}s at timestep {self.timestep} = {data_summary}"


class Timestep:
    def __init__(self, timestep: int):
        self.timestep = timestep
        self._fields_dict = {"Total": {}, "External": {}, "Self": {}}
        self._phases_dict = defaultdict(dict)
        self._raw_dict = defaultdict(dict)

        # User uses these attributes to dynamically resolve a given field, phase, 
        # or raw file using Container __getattr__ dunder function.
        self.fields = Container(
            data_dict=self._fields_dict, 
            timestep=timestep, 
            container_type="Field", 
            kwarg="origin", 
            default_kwarg_value="Total"
        )
        self.phases = Container(
            data_dict=self._phases_dict, 
            timestep=timestep, 
            container_type="Phase", 
            kwarg="species", 
            default_kwarg_value=1
        )
        self.raw_files = Container(
            data_dict=self._raw_dict, 
            timestep=timestep, 
            container_type="Raw file", 
            kwarg="species", 
            default_kwarg_value=1
        )

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