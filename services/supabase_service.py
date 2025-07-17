import os
import asyncio
from supabase import create_client, Client
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from models.unified_lead import UnifiedLead, LeadStatus

class SupabaseService:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not all([self.supabase_url, self.supabase_key]):
            raise ValueError("Missing required Supabase credentials")
        
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
    
    # Lead Operations
    async def create_lead(self, lead: UnifiedLead) -> UnifiedLead:
        """Create a new lead"""
        try:
            lead_data = lead.dict()
            lead_data["created_at"] = datetime.utcnow().isoformat()
            lead_data["updated_at"] = datetime.utcnow().isoformat()
            
            result = self.client.table("leads").insert(lead_data).execute()
            
            if result.data:
                return UnifiedLead(**result.data[0])
            else:
                raise Exception("Failed to create lead")
                
        except Exception as e:
            print(f"Error creating lead: {e}")
            raise e
    
    async def get_leads(self, skip: int = 0, limit: int = 100) -> List[Lead]:
        """Get leads with pagination"""
        try:
            result = self.client.table("leads").select("*").range(skip, skip + limit - 1).execute()
            
            if result.data:
                return [Lead(**lead) for lead in result.data]
            else:
                return []
                
        except Exception as e:
            print(f"Error getting leads: {e}")
            return []
    
    async def get_lead(self, lead_id: str) -> Optional[Lead]:
        """Get a specific lead by ID"""
        try:
            result = self.client.table("leads").select("*").eq("id", lead_id).execute()
            
            if result.data:
                return UnifiedLead(**result.data[0])
            else:
                return None
                
        except Exception as e:
            print(f"Error getting lead: {e}")
            return None
    
    async def update_lead(self, lead_id: str, lead: Lead) -> Lead:
        """Update a lead"""
        try:
            lead_data = lead.dict(exclude_unset=True)
            lead_data["updated_at"] = datetime.utcnow().isoformat()
            
            result = self.client.table("leads").update(lead_data).eq("id", lead_id).execute()
            
            if result.data:
                return UnifiedLead(**result.data[0])
            else:
                raise Exception("Failed to update lead")
                
        except Exception as e:
            print(f"Error updating lead: {e}")
            raise e
    
    async def update_lead_status(self, lead_id: str, status: LeadStatus) -> bool:
        """Update lead status"""
        try:
            result = self.client.table("leads").update({
                "status": status.value,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", lead_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            print(f"Error updating lead status: {e}")
            return False
    
    # Call Log Operations
    async def create_call_log(self, call_log: CallLog) -> CallLog:
        """Create a new call log"""
        try:
            call_data = call_log.dict()
            call_data["created_at"] = datetime.utcnow().isoformat()
            call_data["updated_at"] = datetime.utcnow().isoformat()
            
            result = self.client.table("call_logs").insert(call_data).execute()
            
            if result.data:
                return CallLog(**result.data[0])
            else:
                raise Exception("Failed to create call log")
                
        except Exception as e:
            print(f"Error creating call log: {e}")
            raise e
    
    async def get_call_logs(self, skip: int = 0, limit: int = 100) -> List[CallLog]:
        """Get call logs with pagination"""
        try:
            result = self.client.table("call_logs").select("*").range(skip, skip + limit - 1).order("created_at", desc=True).execute()
            
            if result.data:
                return [CallLog(**call) for call in result.data]
            else:
                return []
                
        except Exception as e:
            print(f"Error getting call logs: {e}")
            return []
    
    async def get_call_log(self, call_id: str) -> Optional[CallLog]:
        """Get a specific call log by ID"""
        try:
            result = self.client.table("call_logs").select("*").eq("id", call_id).execute()
            
            if result.data:
                return CallLog(**result.data[0])
            else:
                return None
                
        except Exception as e:
            print(f"Error getting call log: {e}")
            return None
    
    async def get_call_logs_by_lead(self, lead_id: str) -> List[CallLog]:
        """Get all call logs for a specific lead"""
        try:
            result = self.client.table("call_logs").select("*").eq("lead_id", lead_id).order("created_at", desc=True).execute()
            
            if result.data:
                return [CallLog(**call) for call in result.data]
            else:
                return []
                
        except Exception as e:
            print(f"Error getting call logs for lead: {e}")
            return []
    
    async def update_call_log_status(self, call_log_id: str, status: str) -> bool:
        """Update call log status"""
        try:
            result = self.client.table("call_logs").update({
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", call_log_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            print(f"Error updating call log status: {e}")
            return False
    
    async def update_call_log_outcome(self, call_log_id: str, outcome: CallOutcome, transcript: List[Dict], duration: int = None) -> bool:
        """Update call log with outcome and transcript"""
        try:
            update_data = {
                "outcome": outcome.value,
                "transcript": transcript,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if duration:
                update_data["duration_sec"] = duration
            
            result = self.client.table("call_logs").update(update_data).eq("id", call_log_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            print(f"Error updating call log outcome: {e}")
            return False
    
    async def store_recording(self, call_log_id: str, recording_url: str) -> bool:
        """Store recording URL in call log"""
        try:
            result = self.client.table("call_logs").update({
                "recording_url": recording_url,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", call_log_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            print(f"Error storing recording: {e}")
            return False
    
    # Statistics and Analytics
    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics"""
        try:
            # Get lead counts by status
            leads_result = self.client.table("leads").select("status", count="exact").execute()
            
            # Get call statistics
            calls_result = self.client.table("call_logs").select("outcome", count="exact").execute()
            
            # Process results
            lead_stats = {}
            if leads_result.data:
                for lead in leads_result.data:
                    status = lead.get("status", "new")
                    lead_stats[status] = lead_stats.get(status, 0) + 1
            
            call_stats = {}
            if calls_result.data:
                for call in calls_result.data:
                    outcome = call.get("outcome", "unknown")
                    call_stats[outcome] = call_stats.get(outcome, 0) + 1
            
            return {
                "total_leads": leads_result.count or 0,
                "lead_stats": lead_stats,
                "call_stats": call_stats
            }
            
        except Exception as e:
            print(f"Error getting dashboard stats: {e}")
            return {"total_leads": 0, "lead_stats": {}, "call_stats": {}}
    
    # File Storage (using Supabase Storage)
    async def upload_file(self, bucket_name: str, file_name: str, file_data: bytes) -> Optional[str]:
        """Upload file to Supabase Storage"""
        try:
            result = self.client.storage.from_(bucket_name).upload(file_name, file_data)
            
            if result.get("error"):
                print(f"Error uploading file: {result['error']}")
                return None
            
            # Get public URL
            public_url = self.client.storage.from_(bucket_name).get_public_url(file_name)
            return public_url
            
        except Exception as e:
            print(f"Error uploading file: {e}")
            return None