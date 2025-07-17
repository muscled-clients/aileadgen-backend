from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class LandingLead(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    first_name: str
    last_name: str
    email: str
    phone: str
    is_serious: str
    monthly_revenue: str
    pain_point: str
    marketing_budget: str
    qualified: bool = False
    niche: Optional[str] = "real-estate"
    source: Optional[str] = "landing-page"
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class LandingLeadCreateRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str
    is_serious: str
    monthly_revenue: str
    pain_point: str
    marketing_budget: str
    qualified: bool = False
    niche: Optional[str] = "real-estate"