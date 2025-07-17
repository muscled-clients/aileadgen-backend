"""
Simple Lead Service - File-based storage for local development
"""

import json
import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from models.unified_lead import UnifiedLead, LeadCreateRequest, LeadUpdateRequest, LeadStatus, CompletionStatus

class SimpleLeadService:
    """
    Simple Lead Service - uses local file storage
    Perfect for local development without external dependencies
    """
    
    def __init__(self):
        self.database_dir = "database"
        self.leads_file = os.path.join(self.database_dir, "leads.json")
        
        # Create database directory if it doesn't exist
        os.makedirs(self.database_dir, exist_ok=True)
        
        # Initialize leads file if it doesn't exist
        if not os.path.exists(self.leads_file):
            with open(self.leads_file, 'w') as f:
                json.dump([], f)
    
    def _load_leads(self) -> List[Dict]:
        """Load leads from file"""
        try:
            with open(self.leads_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _save_leads(self, leads: List[Dict]):
        """Save leads to file"""
        with open(self.leads_file, 'w') as f:
            json.dump(leads, f, indent=2)
    
    async def create_lead(self, request: LeadCreateRequest) -> UnifiedLead:
        """Create a new lead"""
        try:
            # Convert request to unified lead
            lead = request.to_unified_lead()
            
            # Validate lead
            if not lead.name and not (lead.first_name and lead.last_name):
                raise ValueError("Lead must have name or first_name + last_name")
            
            if not lead.phone_number:
                raise ValueError("Phone number is required")
            
            # Auto-determine completion status if not provided
            if not request.completion_status:
                # Check if this is just basic contact info (name, email, phone)
                has_qualification_data = any([
                    lead.monthly_revenue,
                    lead.marketing_budget,
                    lead.pain_point,
                    lead.is_serious,
                    lead.qualified is not None
                ])
                
                if has_qualification_data:
                    # Has some qualification data
                    complete_fields = [
                        lead.monthly_revenue,
                        lead.marketing_budget,
                        lead.pain_point,
                        lead.is_serious,
                        lead.qualified is not None
                    ]
                    if all(complete_fields):
                        lead.completion_status = CompletionStatus.COMPLETE
                    else:
                        lead.completion_status = CompletionStatus.PARTIAL
                else:
                    # Only basic contact info
                    lead.completion_status = CompletionStatus.INCOMPLETE
            
            # Set timestamps with timezone info
            now = datetime.now(timezone.utc).isoformat()
            lead.created_at = now
            lead.updated_at = now
            
            # Load existing leads
            leads = self._load_leads()
            
            # Add new lead
            leads.append(lead.dict())
            
            # Save leads
            self._save_leads(leads)
            
            return lead
            
        except Exception as e:
            print(f"Error creating lead: {e}")
            raise
    
    async def get_leads(self, skip: int = 0, limit: int = 100) -> List[UnifiedLead]:
        """Get all leads sorted by newest first"""
        try:
            leads_data = self._load_leads()
            
            # Sort by created_at in descending order (newest first)
            leads_data.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # Apply pagination
            paginated_leads = leads_data[skip:skip + limit]
            
            # Convert to UnifiedLead objects
            leads = []
            for lead_data in paginated_leads:
                try:
                    lead = UnifiedLead(**lead_data)
                    leads.append(lead)
                except Exception as e:
                    print(f"Error parsing lead {lead_data.get('id', 'unknown')}: {e}")
                    continue
            
            return leads
            
        except Exception as e:
            print(f"Error getting leads: {e}")
            return []
    
    async def get_lead_by_id(self, lead_id: str) -> Optional[UnifiedLead]:
        """Get a specific lead by ID"""
        try:
            leads_data = self._load_leads()
            
            for lead_data in leads_data:
                if lead_data.get('id') == lead_id:
                    return UnifiedLead(**lead_data)
            
            return None
            
        except Exception as e:
            print(f"Error getting lead by ID: {e}")
            return None
    
    async def update_lead(self, lead_id: str, request: LeadUpdateRequest) -> Optional[UnifiedLead]:
        """Update an existing lead"""
        try:
            leads_data = self._load_leads()
            
            for i, lead_data in enumerate(leads_data):
                if lead_data.get('id') == lead_id:
                    # Update fields
                    update_data = request.dict(exclude_unset=True)
                    lead_data.update(update_data)
                    lead_data['updated_at'] = datetime.now(timezone.utc).isoformat()
                    
                    # Auto-update completion status if not explicitly provided
                    if 'completion_status' not in update_data:
                        # Check completion status based on current data
                        has_qualification_data = any([
                            lead_data.get('monthly_revenue'),
                            lead_data.get('marketing_budget'),
                            lead_data.get('pain_point'),
                            lead_data.get('is_serious'),
                            lead_data.get('qualified') is not None
                        ])
                        
                        if has_qualification_data:
                            # Has some qualification data
                            complete_fields = [
                                lead_data.get('monthly_revenue'),
                                lead_data.get('marketing_budget'),
                                lead_data.get('pain_point'),
                                lead_data.get('is_serious'),
                                lead_data.get('qualified') is not None
                            ]
                            if all(complete_fields):
                                lead_data['completion_status'] = CompletionStatus.COMPLETE
                            else:
                                lead_data['completion_status'] = CompletionStatus.PARTIAL
                        else:
                            # Only basic contact info
                            lead_data['completion_status'] = CompletionStatus.INCOMPLETE
                    
                    # Save leads
                    self._save_leads(leads_data)
                    
                    return UnifiedLead(**lead_data)
            
            return None
            
        except Exception as e:
            print(f"Error updating lead: {e}")
            return None
    
    async def delete_lead(self, lead_id: str) -> bool:
        """Delete a lead"""
        try:
            leads_data = self._load_leads()
            
            for i, lead_data in enumerate(leads_data):
                if lead_data.get('id') == lead_id:
                    del leads_data[i]
                    self._save_leads(leads_data)
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error deleting lead: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get lead statistics"""
        try:
            leads_data = self._load_leads()
            
            total_leads = len(leads_data)
            
            # Count by status
            status_counts = {}
            qualified_count = 0
            unqualified_count = 0
            
            for lead_data in leads_data:
                status = lead_data.get('status', 'new')
                status_counts[status] = status_counts.get(status, 0) + 1
                
                if lead_data.get('qualified') is True:
                    qualified_count += 1
                elif lead_data.get('qualified') is False:
                    unqualified_count += 1
            
            return {
                'total_leads': total_leads,
                'status_counts': status_counts,
                'qualified_count': qualified_count,
                'unqualified_count': unqualified_count
            }
            
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {
                'total_leads': 0,
                'status_counts': {},
                'qualified_count': 0,
                'unqualified_count': 0
            }