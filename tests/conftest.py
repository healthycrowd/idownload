import pytest
from networktest import NetworkBlocker


@pytest.fixture(scope="module", autouse=True)
def networkblocker():
    with NetworkBlocker():
        yield
