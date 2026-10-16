from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

Category = Literal["camera", "drone", "audio", "lab_kit", "laptop", "vr"]
AssetState = Literal["in_service", "maintenance", "retired"]
LoanStatus = Literal["reserved", "checked_out", "returned", "cancelled"]

TAG_PATTERN = r"^[A-Z]{2,5}-[0-9]{2,4}$"
ROLL_PATTERN = r"^[0-9]{2}[A-Z]{2,4}[0-9]{3,6}$"


class _Trimmed(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class AssetCreate(_Trimmed):
    tag: str = Field(pattern=TAG_PATTERN, examples=["CAM-014"])
    name: str = Field(min_length=2, max_length=120)
    category: Category
    location: str = Field(default="", max_length=120)
    notes: str = Field(default="", max_length=2000)
    state: AssetState = "in_service"

    @field_validator("tag", mode="before")
    @classmethod
    def upper_tag(cls, v):
        return v.strip().upper() if isinstance(v, str) else v


class AssetUpdate(_Trimmed):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    category: Category | None = None
    location: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)
    state: AssetState | None = None


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tag: str
    name: str
    category: Category
    state: AssetState
    location: str
    notes: str
    created_at: datetime
    updated_at: datetime
    available_now: bool = False
    current_loan_id: int | None = None
    next_reservation: date | None = None


class LoanCreate(_Trimmed):
    asset_id: int = Field(gt=0)
    borrower_name: str = Field(min_length=2, max_length=80)
    borrower_roll: str = Field(pattern=ROLL_PATTERN, examples=["24BCS10329"])
    borrower_email: EmailStr
    purpose: str = Field(default="", max_length=200)
    start_date: date
    due_date: date

    @field_validator("borrower_roll", mode="before")
    @classmethod
    def upper_roll(cls, v):
        return v.strip().upper() if isinstance(v, str) else v

    @model_validator(mode="after")
    def due_after_start(self):
        if self.due_date <= self.start_date:
            raise ValueError("due_date must be after start_date")
        return self


class LoanUpdate(_Trimmed):
    start_date: date | None = None
    due_date: date | None = None
    purpose: str | None = Field(default=None, max_length=200)


class LoanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    asset_tag: str
    asset_name: str
    asset_category: Category
    borrower_name: str
    borrower_roll: str
    borrower_email: str
    purpose: str
    start_date: date
    due_date: date
    status: LoanStatus
    checked_out_at: datetime | None
    returned_at: datetime | None
    created_at: datetime
    updated_at: datetime
    overdue: bool
    days_overdue: int
    returned_late: bool


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    at: datetime
    entity: str
    entity_id: int
    action: str
    summary: str


class StatsOut(BaseModel):
    assets_total: int
    assets_in_service: int
    assets_available_now: int
    loans_by_status: dict[str, int]
    on_loan_now: int
    overdue: int
    due_today: int
    utilisation_pct: float
    by_category: dict[str, int]


class Rules(BaseModel):
    max_active_loans: int
    max_advance_days: int
    max_loan_days: dict[str, int]


class InfoOut(BaseModel):
    app: str
    version: str
    environment: str
    pod: str
    today: date
    timezone: str
    categories: list[str]
    asset_states: list[str]
    rules: Rules
