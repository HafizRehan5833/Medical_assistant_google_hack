from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator # type: ignore


class MedicineModel(BaseModel):
    """Pydantic v2 model representing a medicine entry from `medicine_data.json`.

    Uses field aliases so callers can provide keys like "Medicine Name" or
    the normalized attribute names.
    """

    medicine_name: str = Field(..., alias="Medicine Name")
    composition: Optional[str] = Field(None, alias="Composition")
    uses: Optional[str] = Field(None, alias="Uses")
    side_effects: Optional[str] = Field(None, alias="Side_effects")

    excellent_review_pct: Optional[int] = Field(None, alias="Excellent Review %")
    average_review_pct: Optional[int] = Field(None, alias="Average Review %")
    poor_review_pct: Optional[int] = Field(None, alias="Poor Review %")

    # Convert incoming percent-like values to ints (before other validation)
    @field_validator('excellent_review_pct', 'average_review_pct', 'poor_review_pct', mode='before')
    def _to_int_if_possible(cls, v):
        if v is None:
            return None
        try:
            return int(v)
        except Exception:
            raise ValueError('percent fields must be int-convertible')

    # After model creation, ensure percent ranges and totals are sensible
    @model_validator(mode='after')
    def _check_percent_ranges_and_total(self):
        total = 0
        for v in (self.excellent_review_pct, self.average_review_pct, self.poor_review_pct):
            if v is None:
                continue
            if not (0 <= v <= 100):
                raise ValueError('review percent values must be between 0 and 100')
            total += v
        if total > 100:
            raise ValueError('Sum of review percentages cannot exceed 100')
        return self

    # Pydantic v2 model config
    model_config = {
        'populate_by_name': True,
        'anystr_strip_whitespace': True,
        'json_schema_extra': {
            "example": {
                "Medicine Name": "Augmentin 625 Duo Tablet",
                "Composition": "Amoxycillin  (500mg) +  Clavulanic Acid (125mg)",
                "Uses": "Treatment of Bacterial infections",
                "Side_effects": "Vomiting Nausea Diarrhea Mucocutaneous candidiasis",
                "Excellent Review %": 47,
                "Average Review %": 35,
                "Poor Review %": 18
            }
        }
    }
