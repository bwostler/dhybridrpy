import pytest
from dhybridrpy.containers import Container, Timestep
from dhybridrpy.data import Field, Phase, Raw

@pytest.fixture
def mock_field():
    return Field(name="Bx", type="Total", data=None)

@pytest.fixture
def mock_phase():
    return Phase(name="x", species=1, data=None)

@pytest.fixture
def mock_raw():
    return Raw(name="position", species=1, data=None)

@pytest.fixture
def container():
    data = {"Total": {"Bx": Field(name="Bx", type="Total", data=None)}}
    return Container(data, timestep=0, container_type="field", kwarg="type", default_kwarg_value="Total")

def test_container_init(container):
    assert container.timestep == 0
    assert container.type == "Field"
    assert container.kwarg == "type"
    assert container.default_kwarg_value == "Total"

def test_container_getattr_errors(container):
    with pytest.raises(TypeError, match="Expected at most one argument"):
        container.Bx("Total", type="Total")
    
    with pytest.raises(TypeError, match="Argument name 'invalid' must be 'type'"):
        container.Bx(invalid="Total")

def test_container_data_retrieval(container):
    field = container.Bx()  # Should use default type="Total"
    assert isinstance(field, Field)
    assert field.name == "Bx"
    
    field = container.Bx(type="Total")
    assert isinstance(field, Field)
    assert field.name == "Bx"

def test_timestep_init():
    ts = Timestep(0)
    assert ts.timestep == 0
    assert isinstance(ts.fields, Container)
    assert isinstance(ts.phases, Container)
    assert isinstance(ts.raw_files, Container)

def test_timestep_add_field(mock_field):
    ts = Timestep(0)
    ts.add_field(mock_field)
    retrieved_field = ts.fields.Bx()
    assert retrieved_field == mock_field

def test_timestep_add_phase(mock_phase):
    ts = Timestep(0)
    ts.add_phase(mock_phase)
    retrieved_phase = ts.phases.x()
    assert retrieved_phase == mock_phase

def test_timestep_add_raw(mock_raw):
    ts = Timestep(0)
    ts.add_raw(mock_raw)
    retrieved_raw = ts.raw_files.position()
    assert retrieved_raw == mock_raw

def test_timestep_add_field_error():
    ts = Timestep(0)
    invalid_field = Field(name="Bx", type="Invalid", data=None)
    with pytest.raises(ValueError, match="Unknown type 'Invalid'"):
        ts.add_field(invalid_field)