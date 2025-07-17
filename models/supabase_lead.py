"""
Supabase Lead Model - Matches Supabase database schema
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
from datetime import datetime
from enum import Enum
import uuid

class LeadStatus(str, Enum):
    """Lead status enumeration"""
    NEW = "new"
    CALLED = "called"
    BOOKED = "booked"
    CALLBACK = "callback"
    NOT_ANSWERED = "not_answered"
    FAILED = "failed"

class LeadSource(str, Enum):
    """Lead source enumeration"""
    LANDING_PAGE = "landing_page"
    CALL_SYSTEM = "call_system"
    IMPORT = "import"
    MANUAL = "manual"

class CompletionStatus(str, Enum):
    """Form completion status for progressive data collection"""
    INCOMPLETE = "incomplete"  # Only basic contact info provided
    PARTIAL = "partial"        # Some additional fields filled
    COMPLETE = "complete"      # All form fields completed

class SupabaseLead(BaseModel):
    """
    Supabase Lead Model - matches database schema exactly
    """
    id: Optional[str] = None
    
    # Core fields (required)
    first_name: str = Field(..., min_length=1, max_length=200)
    last_name: str = Field(..., min_length=1, max_length=200)
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    
    # Landing page specific fields
    niche: Optional[str] = "real-estate"
    is_serious: Optional[str] = None
    monthly_revenue: Optional[str] = None
    pain_point: Optional[str] = None
    marketing_budget: Optional[str] = None
    qualified: Optional[bool] = False
    completion_status: Optional[str] = "incomplete"
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True

class SupabaseLeadCreateRequest(BaseModel):
    """Request model for creating leads in Supabase"""
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    niche: Optional[str] = "real-estate"
    is_serious: Optional[str] = None
    monthly_revenue: Optional[str] = None
    pain_point: Optional[str] = None
    marketing_budget: Optional[str] = None
    qualified: Optional[bool] = False
    completion_status: Optional[str] = "incomplete"

class SupabaseLeadUpdateRequest(BaseModel):
    """Request model for updating leads in Supabase"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    niche: Optional[str] = None
    is_serious: Optional[str] = None
    monthly_revenue: Optional[str] = None
    pain_point: Optional[str] = None
    marketing_budget: Optional[str] = None
    qualified: Optional[bool] = None
    completion_status: Optional[str] = None
    
    class Config:
        use_enum_values = True