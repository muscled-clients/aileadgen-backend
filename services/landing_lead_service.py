import json
import os
from typing import List, Optional
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.landing_lead_models import LandingLead, LandingLeadCreateRequest

class LandingLeadService:
    def __init__(self):
        self.leads_file = "leads.json"
        self.leads = self._load_leads()
    
    def _load_leads(self) -> List[dict]:
        """Load leads from JSON file"""
        if os.path.exists(self.leads_file):
            try:
                with open(self.leads_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_leads(self):
        """Save leads to JSON file"""
        with open(self.leads_file, 'w') as f:
            json.dump(self.leads, f, indent=2, default=str)
    
    async def create_lead(self, lead_data: LandingLeadCreateRequest) -> LandingLead:
        """Create a new landing page lead"""
        lead = LandingLead(
            **lead_data.dict(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Convert to dict for storage
        lead_dict = lead.dict()
        lead_dict['created_at'] = lead_dict['created_at'].isoformat()
        lead_dict['updated_at'] = lead_dict['updated_at'].isoformat()
        
        self.leads.append(lead_dict)
        self._save_leads()
        
        return lead
    
    async def get_leads(self, skip: int = 0, limit: int = 100) -> List[LandingLead]:
        """Get all landing page leads with pagination"""
        leads_slice = self.leads[skip:skip + limit]
        
        # Convert back to LandingLead objects
        result = []
        for lead_dict in leads_slice:
            # Convert datetime strings back to datetime objects
            if isinstance(lead_dict.get('created_at'), str):
                lead_dict['created_at'] = datetime.fromisoformat(lead_dict['created_at'])
            if isinstance(lead_dict.get('updated_at'), str):
                lead_dict['updated_at'] = datetime.fromisoformat(lead_dict['updated_at'])
            
            result.append(LandingLead(**lead_dict))
        
        return result
    
    async def get_lead(self, lead_id: str) -> Optional[LandingLead]:
        """Get a specific landing page lead by ID"""
        for lead_dict in self.leads:
            if lead_dict['id'] == lead_id:
                # Convert datetime strings back to datetime objects
                if isinstance(lead_dict.get('created_at'), str):
                    lead_dict['created_at'] = datetime.fromisoformat(lead_dict['created_at'])
                if isinstance(lead_dict.get('updated_at'), str):
                    lead_dict['updated_at'] = datetime.fromisoformat(lead_dict['updated_at'])
                
                return LandingLead(**lead_dict)
        return None
    
    async def get_stats(self) -> dict:
        """Get landing page lead statistics"""
        total_leads = len(self.leads)
        qualified_leads = len([l for l in self.leads if l.get('qualified')])
        unqualified_leads = total_leads - qualified_leads
        
        # Revenue breakdown
        revenue_stats = {}
        for lead in self.leads:
            revenue = lead.get('monthly_revenue', 'Unknown')
            revenue_stats[revenue] = revenue_stats.get(revenue, 0) + 1
        
        # Pain point breakdown
        pain_stats = {}
        for lead in self.leads:
            pain = lead.get('pain_point', 'Unknown')
            pain_stats[pain] = pain_stats.get(pain, 0) + 1
        
        return {
            'total_leads': total_leads,
            'qualified_leads': qualified_leads,
            'unqualified_leads': unqualified_leads,
            'revenue_breakdown': revenue_stats,
            'pain_point_breakdown': pain_stats
        }