from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

class LeadStatus(str, Enum):
    NEW = "new"
    CALLED = "called"
    BOOKED = "booked"
    CALLBACK = "callback"
    NOT_ANSWERED = "not_answered"
    FAILED = "failed"

class CallOutcome(str, Enum):
    BOOKED = "booked"
    NOT_ANSWERED = "not_answered"
    CALLBACK = "callback"
    FAILED = "failed"
    COMPLETED = "completed"
    BUSY = "busy"

class Lead(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    phone_number: str
    timezone: Optional[str] = "UTC"
    status: LeadStatus = LeadStatus.NEW
    last_call_time: Optional[datetime] = None
    notes: Optional[str] = ""
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class CallLog(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    lead_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    outcome: Optional[CallOutcome] = None
    transcript: Optional[List[Dict[str, Any]]] = []
    recording_url: Optional[str] = None
    duration_sec: Optional[int] = None
    ai_agent_version: Optional[str] = "1.0.0"
    status: Optional[str] = "pending"
    call_sid: Optional[str] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class CallInitiateRequest(BaseModel):
    lead_id: str
    
class CallUpdateRequest(BaseModel):
    outcome: Optional[CallOutcome] = None
    notes: Optional[str] = None
    
class LeadCreateRequest(BaseModel):
    name: str
    phone_number: str
    timezone: Optional[str] = "UTC"
    notes: Optional[str] = ""
    
class LeadUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = None
    timezone: Optional[str] = None
    status: Optional[LeadStatus] = None
    notes: Optional[str] = None

class TranscriptEntry(BaseModel):
    timestamp: str
    text: str
    speaker: str  # "customer" or "ai"
    confidence: Optional[float] = None

class CallStats(BaseModel):
    total_calls: int
    successful_calls: int
    failed_calls: int
    booked_calls: int
    callback_requests: int
    average_duration: Optional[float] = None

class DashboardStats(BaseModel):
    total_leads: int
    new_leads: int
    called_leads: int
    booked_leads: int
    callback_leads: int
    failed_leads: int
    today_stats: CallStats
    week_stats: CallStats