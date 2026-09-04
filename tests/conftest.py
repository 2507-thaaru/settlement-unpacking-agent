import json
from pathlib import Path

import pytest

from src.schemas import load_all_data

DATA_DIR = Path(__file__).parent.parent / "data"


@pytest.fixture(scope="session")
def ctx():
    return load_all_data(DATA_DIR)


@pytest.fixture(scope="session")
def ground_truth():
    with open(DATA_DIR / "injected_exceptions.json") as f:
        return json.load(f)
