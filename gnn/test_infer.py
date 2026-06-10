import pytest
from infer import get_probability
from train import load_data

def test_get_probability():
    # Load data just to get a valid person_id
    data, _, id_maps = load_data()
    
    # Pick the first person
    valid_person_id = list(id_maps["person"].keys())[0]
    
    # Run inference
    prob = get_probability(valid_person_id)
    
    # Confirm it returns a float in [0, 1]
    assert isinstance(prob, float), "Expected probability to be a float"
    assert 0.0 <= prob <= 1.0, f"Expected probability in [0, 1], got {prob}"

def test_invalid_person_id():
    with pytest.raises(ValueError):
        get_probability("invalid_id_123")
