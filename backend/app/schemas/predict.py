from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator


class CustomerRecord(BaseModel):
    """19-field telecom customer record. All numerics >= 0."""

    # Demographics
    state: str = Field(min_length=2, max_length=2, description="2-char US state code")
    account_length: int = Field(ge=0)
    area_code: int = Field(ge=100, le=999)

    # Plan flags
    international_plan: Literal["yes", "no"]
    voice_mail_plan: Literal["yes", "no"]

    # Voicemail
    number_vmail_messages: int = Field(ge=0)

    # Day usage
    total_day_minutes: float = Field(ge=0)
    total_day_calls: int = Field(ge=0)
    total_day_charge: float = Field(ge=0)

    # Evening usage
    total_eve_minutes: float = Field(ge=0)
    total_eve_calls: int = Field(ge=0)
    total_eve_charge: float = Field(ge=0)

    # Night usage
    total_night_minutes: float = Field(ge=0)
    total_night_calls: int = Field(ge=0)
    total_night_charge: float = Field(ge=0)

    # International usage
    total_intl_minutes: float = Field(ge=0)
    total_intl_calls: int = Field(ge=0)
    total_intl_charge: float = Field(ge=0)

    # Service
    customer_service_calls: int = Field(ge=0)

    @field_validator("state")
    @classmethod
    def state_uppercase(cls, v: str) -> str:
        return v.upper()


class PredictionResult(BaseModel):
    churn: bool
    churn_probability: float = Field(ge=0.0, le=1.0)
    confidence_band: Literal["low", "mid", "high"]
    input_hash: str


class PredictRequest(BaseModel):
    records: list[CustomerRecord] = Field(min_length=1, max_length=500)


class PredictResponse(BaseModel):
    predictions: list[PredictionResult]
    model_version: str
    record_count: int
    latency_ms: float
