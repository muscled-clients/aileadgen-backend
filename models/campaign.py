"""
Campaign Model - For managing lead campaigns
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

class CampaignStatus(str, Enum):
    """Campaign status enum"""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Campaign(BaseModel):
    """
    Campaign model for managing lead campaigns
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    
    # Campaign settings
    status: CampaignStatus = Field(default=CampaignStatus.CREATED)
    niche: Optional[str] = Field(None, max_length=50)
    
    # Lead tracking
    lead_ids: List[str] = Field(default_factory=list)
    total_leads: int = Field(default=0)
    called_leads: int = Field(default=0)
    successful_calls: int = Field(default=0)
    failed_calls: int = Field(default=0)
    
    # Timestamps
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = Field(None)
    completed_at: Optional[str] = Field(None)
    
    # Metadata
    created_by: Optional[str] = Field(None)
    settings: Dict[str, Any] = Field(default_factory=dict)

    def __post_init__(self):
        """Set total_leads from lead_ids"""
        if self.lead_ids:
            self.total_leads = len(self.lead_ids)

class CampaignCreateRequest(BaseModel):
    """Request model for creating campaigns"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    lead_ids: List[str] = Field(..., min_items=1)
    niche: Optional[str] = Field(None, max_length=50)
    settings: Dict[str, Any] = Field(default_factory=dict)

    def to_campaign(self) -> Campaign:
        """Convert request to campaign model"""
        return Campaign(
            name=self.name,
            description=self.description,
            lead_ids=self.lead_ids,
            niche=self.niche,
            total_leads=len(self.lead_ids),
            settings=self.settings
        )

class CampaignUpdateRequest(BaseModel):
    """Request model for updating campaigns"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[CampaignStatus] = Field(None)
    settings: Optional[Dict[str, Any]] = Field(None)

class CampaignStats(BaseModel):
    """Campaign statistics model"""
    total_campaigns: int = Field(default=0)
    active_campaigns: int = Field(default=0)
    completed_campaigns: int = Field(default=0)
    total_leads_in_campaigns: int = Field(default=0)
    total_calls_made: int = Field(default=0)
    success_rate: float = Field(default=0.0)