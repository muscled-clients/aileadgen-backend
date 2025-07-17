"""
Unified Lead Model - Single source of truth for all lead data
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

class UnifiedLead(BaseModel):
    """
    Unified Lead Model - handles all lead types
    Consolidates previous Lead and LandingLead models
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Core fields (required)
    name: str = Field(..., min_length=1, max_length=200)
    phone_number: str = Field(..., min_length=10, max_length=20)
    email: Optional[str] = Field(None, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    
    # Status and source
    status: LeadStatus = LeadStatus.NEW
    source: LeadSource = LeadSource.MANUAL
    completion_status: CompletionStatus = CompletionStatus.INCOMPLETE
    
    # Landing page specific fields
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    monthly_revenue: Optional[str] = None
    marketing_budget: Optional[str] = None
    pain_point: Optional[str] = None
    is_serious: Optional[str] = None
    qualified: Optional[bool] = None
    niche: Optional[str] = "real-estate"
    
    # Call system specific fields
    timezone: Optional[str] = "UTC"
    last_call_time: Optional[datetime] = None
    notes: Optional[str] = ""
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('name', pre=True)
    def set_name_from_parts(cls, v, values):
        """Auto-generate name from first_name and last_name if not provided"""
        if not v and values.get('first_name') and values.get('last_name'):
            return f"{values['first_name']} {values['last_name']}"
        return v
    
    @validator('phone_number')
    def validate_phone(cls, v):
        """Validate phone number format"""
        if not v:
            raise ValueError('Phone number is required')
        
        # Remove all non-digit characters except +
        cleaned = ''.join(c for c in v if c.isdigit() or c == '+')
        
        # Remove + and check digit count
        digits_only = cleaned.replace('+', '')
        if len(digits_only) < 10 or len(digits_only) > 15:
            raise ValueError('Phone number must be between 10-15 digits')
        
        return v
    
    @validator('email')
    def validate_email(cls, v):
        """Validate email format"""
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v

class LeadCreateRequest(BaseModel):
    """Request model for creating leads"""
    # Core fields
    name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    
    # Landing page fields
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None  # Alternative field name
    monthly_revenue: Optional[str] = None
    marketing_budget: Optional[str] = None
    pain_point: Optional[str] = None
    is_serious: Optional[str] = None
    qualified: Optional[bool] = None
    niche: Optional[str] = "real-estate"
    
    # Call system fields
    timezone: Optional[str] = "UTC"
    notes: Optional[str] = ""
    
    # Form completion tracking
    completion_status: Optional[CompletionStatus] = CompletionStatus.INCOMPLETE
    
    def to_unified_lead(self) -> UnifiedLead:
        """Convert request to UnifiedLead"""
        # Determine source based on fields present
        source = LeadSource.LANDING_PAGE if self.first_name or self.phone else LeadSource.CALL_SYSTEM
        
        # Use phone or phone_number
        phone = self.phone_number or self.phone
        
        # Construct name from first_name and last_name if name is not provided
        name = self.name
        if not name and self.first_name and self.last_name:
            name = f"{self.first_name} {self.last_name}"
        elif not name and self.first_name:
            name = self.first_name
        elif not name and self.last_name:
            name = self.last_name
        
        return UnifiedLead(
            name=name,
            phone_number=phone,
            email=self.email,
            first_name=self.first_name,
            last_name=self.last_name,
            monthly_revenue=self.monthly_revenue,
            marketing_budget=self.marketing_budget,
            pain_point=self.pain_point,
            is_serious=self.is_serious,
            qualified=self.qualified,
            niche=self.niche,
            timezone=self.timezone,
            notes=self.notes,
            source=source,
            completion_status=self.completion_status or CompletionStatus.INCOMPLETE
        )

class LeadUpdateRequest(BaseModel):
    """Request model for updating leads"""
    name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    status: Optional[LeadStatus] = None
    notes: Optional[str] = None
    qualified: Optional[bool] = None
    
    # Landing page fields for progressive updates
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    monthly_revenue: Optional[str] = None
    marketing_budget: Optional[str] = None
    pain_point: Optional[str] = None
    is_serious: Optional[str] = None
    niche: Optional[str] = None
    completion_status: Optional[CompletionStatus] = None
    
    class Config:
        use_enum_values = True