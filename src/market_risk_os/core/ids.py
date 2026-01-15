"""ID type definitions."""

from typing import NewType


# ID types for various entities
PressureID = NewType("PressureID", str)
InteractionID = NewType("InteractionID", str)
StateID = NewType("StateID", str)
GateID = NewType("GateID", str)


