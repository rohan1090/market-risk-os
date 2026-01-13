"""Pydantic v2 models for market risk with strict validation."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .enums import (
    BehaviorType,
    Directionality,
    InteractionType,
    PressureType,
    RiskState as RiskStateEnum,
)
from .ids import GateID, InteractionID, PressureID, StateID
from .time import ensure_utc


class Pressure(BaseModel):
    """Market pressure model."""
    
    pressure_id: PressureID
    pressure_type: PressureType
    source_assets: List[str] = Field(default_factory=list, description="Asset identifiers")
    directionality: Directionality
    magnitude: float = Field(ge=0.0, le=1.0, description="Magnitude in [0, 1]")
    acceleration: float = Field(ge=-1.0, le=1.0, description="Acceleration in [-1, 1]")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in [0, 1]")
    detected_at: datetime
    time_horizon: Optional[str] = Field(default=None, description="Time horizon description")
    explanation: Optional[str] = Field(default=None, description="Explanation of the pressure")
    
    @field_validator("detected_at", mode="before")
    @classmethod
    def validate_detected_at(cls, v: Any) -> datetime:
        """Ensure detected_at is timezone-aware UTC."""
        if isinstance(v, datetime):
            return ensure_utc(v)
        return ensure_utc()
    
    @field_validator("magnitude", "confidence", mode="after")
    @classmethod
    def validate_range_0_1(cls, v: float) -> float:
        """Validate values are in [0, 1] range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Value must be in [0, 1] range, got {v}")
        return v
    
    @field_validator("acceleration", mode="after")
    @classmethod
    def validate_acceleration_range(cls, v: float) -> float:
        """Validate acceleration is in [-1, 1] range."""
        if not -1.0 <= v <= 1.0:
            raise ValueError(f"Acceleration must be in [-1, 1] range, got {v}")
        return v
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return self.model_dump_json(exclude_none=True)
    
    @classmethod
    def json_schema(cls) -> Dict[str, Any]:
        """Export JSON Schema for this model."""
        return cls.model_json_schema()


class PressureInteraction(BaseModel):
    """Interaction between multiple pressures."""
    
    interaction_id: InteractionID
    pressures_involved: List[PressureID] = Field(
        min_length=2, description="At least two pressure IDs required"
    )
    interaction_type: InteractionType
    instability_contribution: float = Field(
        ge=0.0, le=1.0, description="Instability contribution in [0, 1]"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in [0, 1]")
    explanation: Optional[str] = Field(default=None, description="Explanation of the interaction")
    
    @field_validator("instability_contribution", "confidence", mode="after")
    @classmethod
    def validate_range_0_1(cls, v: float) -> float:
        """Validate values are in [0, 1] range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Value must be in [0, 1] range, got {v}")
        return v
    
    @field_validator("pressures_involved", mode="after")
    @classmethod
    def validate_pressures_count(cls, v: List[PressureID]) -> List[PressureID]:
        """Ensure at least two pressures are involved."""
        if len(v) < 2:
            raise ValueError("At least two pressures must be involved in an interaction")
        return v
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return self.model_dump_json(exclude_none=True)
    
    @classmethod
    def json_schema(cls) -> Dict[str, Any]:
        """Export JSON Schema for this model."""
        return cls.model_json_schema()


class RiskState(BaseModel):
    """Risk state model."""
    
    state_id: StateID
    dominant_state: RiskStateEnum
    contributing_pressures: List[PressureID] = Field(
        default_factory=list, description="Contributing pressure IDs"
    )
    interactions: List[InteractionID] = Field(
        default_factory=list, description="Relevant interaction IDs"
    )
    instability_score: float = Field(ge=0.0, le=1.0, description="Instability score in [0, 1]")
    directional_bias: Optional[Directionality] = Field(
        default=None, description="Directional bias if applicable"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in [0, 1]")
    ambiguity: float = Field(ge=0.0, le=1.0, description="Ambiguity level in [0, 1]")
    valid_horizons: List[str] = Field(
        default_factory=list, description="Valid time horizons for this state"
    )
    detected_at: datetime
    explanation: Optional[str] = Field(default=None, description="Explanation of the risk state")
    
    @field_validator("detected_at", mode="before")
    @classmethod
    def validate_detected_at(cls, v: Any) -> datetime:
        """Ensure detected_at is timezone-aware UTC."""
        if isinstance(v, datetime):
            return ensure_utc(v)
        return ensure_utc()
    
    @field_validator("instability_score", "confidence", "ambiguity", mode="after")
    @classmethod
    def validate_range_0_1(cls, v: float) -> float:
        """Validate values are in [0, 1] range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Value must be in [0, 1] range, got {v}")
        return v
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return self.model_dump_json(exclude_none=True)
    
    @classmethod
    def json_schema(cls) -> Dict[str, Any]:
        """Export JSON Schema for this model."""
        return cls.model_json_schema()


class BehaviorGate(BaseModel):
    """Gate controlling allowed and forbidden behaviors."""
    
    gate_id: GateID
    risk_state_id: StateID
    allowed_behaviors: List[BehaviorType] = Field(
        default_factory=list, description="Allowed behavior types"
    )
    forbidden_behaviors: List[BehaviorType] = Field(
        default_factory=list, description="Forbidden behavior types"
    )
    aggressiveness_limit: float = Field(
        ge=0.0, le=1.0, description="Aggressiveness limit in [0, 1]"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in [0, 1]")
    enforced_until: datetime
    explanation: Optional[str] = Field(default=None, description="Explanation of the gate")
    
    @field_validator("enforced_until", mode="before")
    @classmethod
    def validate_enforced_until(cls, v: Any) -> datetime:
        """Ensure enforced_until is timezone-aware UTC."""
        if isinstance(v, datetime):
            return ensure_utc(v)
        return ensure_utc()
    
    @field_validator("aggressiveness_limit", "confidence", mode="after")
    @classmethod
    def validate_range_0_1(cls, v: float) -> float:
        """Validate values are in [0, 1] range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Value must be in [0, 1] range, got {v}")
        return v
    
    @model_validator(mode="after")
    def validate_behaviors_exclusive(self) -> "BehaviorGate":
        """Ensure allowed and forbidden behaviors don't overlap."""
        overlap = set(self.allowed_behaviors) & set(self.forbidden_behaviors)
        if overlap:
            raise ValueError(
                f"Behaviors cannot be both allowed and forbidden: {overlap}"
            )
        return self
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return self.model_dump_json(exclude_none=True)
    
    @classmethod
    def json_schema(cls) -> Dict[str, Any]:
        """Export JSON Schema for this model."""
        return cls.model_json_schema()


# Helper functions for JSON serialization and schema export

def serialize_to_json(model: BaseModel, indent: Optional[int] = None) -> str:
    """
    Serialize a Pydantic model to JSON string.
    
    Args:
        model: Pydantic model instance
        indent: Optional indentation for pretty printing
    
    Returns:
        JSON string representation
    """
    return model.model_dump_json(exclude_none=True, indent=indent)


def export_json_schema(model_class: type[BaseModel]) -> Dict[str, Any]:
    """
    Export JSON Schema for a Pydantic model class.
    
    Args:
        model_class: Pydantic model class
    
    Returns:
        JSON Schema dictionary
    """
    return model_class.model_json_schema()


def export_all_schemas() -> Dict[str, Dict[str, Any]]:
    """
    Export JSON Schemas for all models.
    
    Returns:
        Dictionary mapping model names to their JSON Schemas
    """
    return {
        "Pressure": Pressure.json_schema(),
        "PressureInteraction": PressureInteraction.json_schema(),
        "RiskState": RiskState.json_schema(),
        "BehaviorGate": BehaviorGate.json_schema(),
    }

