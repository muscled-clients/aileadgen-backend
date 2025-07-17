"""
Supabase Lead Service - Production database integration
"""

import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from supabase import create_client, Client
from models.unified_lead import UnifiedLead, LeadCreateRequest, LeadUpdateRequest
from models.supabase_lead import SupabaseLead, SupabaseLeadCreateRequest, SupabaseLeadUpdateRequest

class SupabaseLeadService:
    """
    Lead Service using Supabase for production database storage
    """
    
    def __init__(self):
        # Get Supabase credentials from environment variables
        supabase_url = os.getenv("SUPABASE_URL", "https://tvhvaopzrierymkzrljm.supabase.co")
        supabase_key = os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR2aHZhb3B6cmllcnlta3pybGptIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTI3NjQ4MDcsImV4cCI6MjA2ODM0MDgwN30.otpkoQ72bCrMR805x7g6UhIeV42efJO7qSWTWq2VNmM")
        
        # Create Supabase client
        self.supabase: Client = create_client(supabase_url, supabase_key)
    
    async def create_lead(self, lead_data: LeadCreateRequest) -> Optional[UnifiedLead]:
        """Create a new lead in Supabase"""
        try:
            # Convert to Supabase format
            supabase_lead = SupabaseLeadCreateRequest(
                first_name=lead_data.first_name or "",
                last_name=lead_data.last_name or "",
                email=lead_data.email or "",
                phone=lead_data.phone or lead_data.phone_number or "",
                niche=lead_data.niche or "real-estate",
                is_serious=lead_data.is_serious,
                monthly_revenue=lead_data.monthly_revenue,
                pain_point=lead_data.pain_point,
                marketing_budget=lead_data.marketing_budget,
                qualified=lead_data.qualified or False,
                completion_status=lead_data.completion_status or "incomplete"
            )
            
            # Convert to dictionary
            lead_dict = supabase_lead.dict()
            
            # Add timestamps
            lead_dict['created_at'] = datetime.utcnow().isoformat()
            lead_dict['updated_at'] = datetime.utcnow().isoformat()
            
            # Insert into Supabase
            result = self.supabase.table('leads').insert(lead_dict).execute()
            
            if result.data:
                # Convert back to UnifiedLead for compatibility
                supabase_data = result.data[0]
                return UnifiedLead(
                    id=supabase_data['id'],
                    name=f"{supabase_data['first_name']} {supabase_data['last_name']}",
                    phone_number=supabase_data['phone'] or "",
                    email=supabase_data['email'],
                    first_name=supabase_data['first_name'],
                    last_name=supabase_data['last_name'],
                    niche=supabase_data['niche'],
                    is_serious=supabase_data['is_serious'],
                    monthly_revenue=supabase_data['monthly_revenue'],
                    pain_point=supabase_data['pain_point'],
                    marketing_budget=supabase_data['marketing_budget'],
                    qualified=supabase_data['qualified'],
                    completion_status=supabase_data['completion_status'],
                    created_at=datetime.fromisoformat(supabase_data['created_at'].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(supabase_data['updated_at'].replace('Z', '+00:00'))
                )
            return None
            
        except Exception as e:
            print(f"Error creating lead in Supabase: {e}")
            return None
    
    async def get_leads(self, skip: int = 0, limit: int = 100) -> List[UnifiedLead]:
        """Get all leads from Supabase with pagination"""
        try:
            result = self.supabase.table('leads').select("*").order('created_at', desc=True).range(skip, skip + limit - 1).execute()
            
            leads = []
            for supabase_data in result.data:
                try:
                    # Convert Supabase data to UnifiedLead
                    lead = UnifiedLead(
                        id=supabase_data['id'],
                        name=f"{supabase_data['first_name']} {supabase_data['last_name']}",
                        phone_number=supabase_data['phone'] or "",
                        email=supabase_data['email'],
                        first_name=supabase_data['first_name'],
                        last_name=supabase_data['last_name'],
                        niche=supabase_data['niche'],
                        is_serious=supabase_data['is_serious'],
                        monthly_revenue=supabase_data['monthly_revenue'],
                        pain_point=supabase_data['pain_point'],
                        marketing_budget=supabase_data['marketing_budget'],
                        qualified=supabase_data['qualified'],
                        completion_status=supabase_data['completion_status'],
                        created_at=datetime.fromisoformat(supabase_data['created_at'].replace('Z', '+00:00')),
                        updated_at=datetime.fromisoformat(supabase_data['updated_at'].replace('Z', '+00:00'))
                    )
                    leads.append(lead)
                except Exception as e:
                    print(f"Error parsing lead {supabase_data.get('id', 'unknown')}: {e}")
                    continue
            
            return leads
            
        except Exception as e:
            print(f"Error getting leads from Supabase: {e}")
            return []
    
    async def get_lead_by_id(self, lead_id: str) -> Optional[UnifiedLead]:
        """Get a specific lead by ID from Supabase"""
        try:
            result = self.supabase.table('leads').select("*").eq('id', lead_id).execute()
            
            if result.data:
                return UnifiedLead(**result.data[0])
            return None
            
        except Exception as e:
            print(f"Error getting lead by ID from Supabase: {e}")
            return None
    
    async def update_lead(self, lead_id: str, update_data: LeadUpdateRequest) -> Optional[UnifiedLead]:
        """Update an existing lead in Supabase"""
        try:
            # Convert request to dictionary, excluding unset fields
            update_dict = update_data.dict(exclude_unset=True)
            update_dict['updated_at'] = datetime.utcnow().isoformat()
            
            # Update in Supabase
            result = self.supabase.table('leads').update(update_dict).eq('id', lead_id).execute()
            
            if result.data:
                return UnifiedLead(**result.data[0])
            return None
            
        except Exception as e:
            print(f"Error updating lead in Supabase: {e}")
            return None
    
    async def delete_lead(self, lead_id: str) -> bool:
        """Delete a lead from Supabase"""
        try:
            result = self.supabase.table('leads').delete().eq('id', lead_id).execute()
            return len(result.data) > 0
            
        except Exception as e:
            print(f"Error deleting lead from Supabase: {e}")
            return False
    
    async def get_leads_by_niche(self, niche: str) -> List[UnifiedLead]:
        """Get leads filtered by niche"""
        try:
            result = self.supabase.table('leads').select("*").eq('niche', niche).order('created_at', desc=True).execute()
            
            leads = []
            for lead_data in result.data:
                try:
                    lead = UnifiedLead(**lead_data)
                    leads.append(lead)
                except Exception as e:
                    print(f"Error parsing lead {lead_data.get('id', 'unknown')}: {e}")
                    continue
            
            return leads
            
        except Exception as e:
            print(f"Error getting leads by niche from Supabase: {e}")
            return []
    
    async def get_qualified_leads(self) -> List[UnifiedLead]:
        """Get only qualified leads"""
        try:
            result = self.supabase.table('leads').select("*").eq('qualified', True).order('created_at', desc=True).execute()
            
            leads = []
            for lead_data in result.data:
                try:
                    lead = UnifiedLead(**lead_data)
                    leads.append(lead)
                except Exception as e:
                    print(f"Error parsing lead {lead_data.get('id', 'unknown')}: {e}")
                    continue
            
            return leads
            
        except Exception as e:
            print(f"Error getting qualified leads from Supabase: {e}")
            return []
    
    async def get_lead_stats(self) -> Dict[str, Any]:
        """Get lead statistics"""
        try:
            # Get total leads
            total_result = self.supabase.table('leads').select("id", count="exact").execute()
            total_leads = total_result.count or 0
            
            # Get qualified leads
            qualified_result = self.supabase.table('leads').select("id", count="exact").eq('qualified', True).execute()
            qualified_leads = qualified_result.count or 0
            
            # Get leads by niche
            niche_result = self.supabase.table('leads').select("niche").execute()
            niche_counts = {}
            for lead in niche_result.data:
                niche = lead.get('niche', 'unknown')
                niche_counts[niche] = niche_counts.get(niche, 0) + 1
            
            return {
                'total_leads': total_leads,
                'qualified_leads': qualified_leads,
                'qualification_rate': round((qualified_leads / total_leads * 100) if total_leads > 0 else 0, 2),
                'niche_breakdown': niche_counts
            }
            
        except Exception as e:
            print(f"Error getting lead stats from Supabase: {e}")
            return {
                'total_leads': 0,
                'qualified_leads': 0,
                'qualification_rate': 0,
                'niche_breakdown': {}
            }