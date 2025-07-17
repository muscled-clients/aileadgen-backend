"""
Unified Lead Service - Single service for all lead operations
Replaces multiple lead services with consistent database storage
"""

import json
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from models.unified_lead import UnifiedLead, LeadCreateRequest, LeadUpdateRequest, LeadStatus
# from services.supabase_service import SupabaseService

class UnifiedLeadService:
    """
    Unified Lead Service - handles all lead operations
    Uses database as primary storage with file backup
    """
    
    def __init__(self):
        # self.supabase_service = SupabaseService()
        self.backup_file = "leads_backup.json"
        self.database_dir = "database"
        self.leads_file = os.path.join(self.database_dir, "leads.json")
        
        # Create database directory if it doesn't exist
        os.makedirs(self.database_dir, exist_ok=True)
        
    async def create_lead(self, request: LeadCreateRequest) -> UnifiedLead:
        """
        Create a new lead with validation and proper storage
        """
        try:
            # Convert request to unified lead
            lead = request.to_unified_lead()
            
            # Validate lead
            if not lead.name and not (lead.first_name and lead.last_name):
                raise ValueError("Lead must have name or first_name + last_name")
            
            if not lead.phone_number:
                raise ValueError("Phone number is required")
            
            # Try to save to database first
            try:
                # Convert to database format
                lead_data = self._to_database_format(lead)
                result = await self.supabase_service.create_lead(lead_data)
                
                # Update lead with database ID if successful
                if result and result.get('id'):
                    lead.id = result['id']
                    
            except Exception as db_error:
                print(f"Database save failed, using backup: {db_error}")
                # Save to backup file if database fails
                await self._save_to_backup(lead)
            
            return lead
            
        except Exception as e:
            print(f"Error creating lead: {e}")
            raise
    
    async def get_leads(self, skip: int = 0, limit: int = 100) -> List[UnifiedLead]:
        """
        Get all leads from database with backup fallback
        """
        try:
            # Try database first
            try:
                db_leads = await self.supabase_service.get_leads(skip, limit)
                leads = [self._from_database_format(lead) for lead in db_leads]
                
                # Add backup leads if any
                backup_leads = await self._load_from_backup()
                leads.extend(backup_leads)
                
                return leads
                
            except Exception as db_error:
                print(f"Database load failed, using backup: {db_error}")
                # Fallback to backup file
                return await self._load_from_backup()
                
        except Exception as e:
            print(f"Error getting leads: {e}")
            return []
    
    async def get_lead_by_id(self, lead_id: str) -> Optional[UnifiedLead]:
        """
        Get a specific lead by ID
        """
        try:
            # Try database first
            try:
                db_lead = await self.supabase_service.get_lead(lead_id)
                if db_lead:
                    return self._from_database_format(db_lead)
            except Exception as db_error:
                print(f"Database get failed: {db_error}")
            
            # Check backup file
            backup_leads = await self._load_from_backup()
            for lead in backup_leads:
                if lead.id == lead_id:
                    return lead
                    
            return None
            
        except Exception as e:
            print(f"Error getting lead: {e}")
            return None
    
    async def update_lead(self, lead_id: str, request: LeadUpdateRequest) -> Optional[UnifiedLead]:
        """
        Update an existing lead
        """
        try:
            # Get existing lead
            existing_lead = await self.get_lead_by_id(lead_id)
            if not existing_lead:
                raise ValueError(f"Lead with ID {lead_id} not found")
            
            # Update fields
            update_data = request.dict(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(existing_lead, field):
                    setattr(existing_lead, field, value)
            
            existing_lead.updated_at = datetime.utcnow()
            
            # Try to update in database
            try:
                db_data = self._to_database_format(existing_lead)
                await self.supabase_service.update_lead(lead_id, db_data)
            except Exception as db_error:
                print(f"Database update failed: {db_error}")
                # Update in backup file
                await self._update_in_backup(existing_lead)
            
            return existing_lead
            
        except Exception as e:
            print(f"Error updating lead: {e}")
            raise
    
    async def delete_lead(self, lead_id: str) -> bool:
        """
        Delete a lead
        """
        try:
            # Try database first
            try:
                await self.supabase_service.delete_lead(lead_id)
            except Exception as db_error:
                print(f"Database delete failed: {db_error}")
            
            # Remove from backup
            await self._remove_from_backup(lead_id)
            return True
            
        except Exception as e:
            print(f"Error deleting lead: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get lead statistics
        """
        try:
            leads = await self.get_leads()
            
            total_leads = len(leads)
            status_counts = {}
            source_counts = {}
            qualified_count = 0
            
            for lead in leads:
                # Count by status
                status = lead.status.value if hasattr(lead.status, 'value') else str(lead.status)
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # Count by source
                source = lead.source.value if hasattr(lead.source, 'value') else str(lead.source)
                source_counts[source] = source_counts.get(source, 0) + 1
                
                # Count qualified
                if lead.qualified:
                    qualified_count += 1
            
            return {
                'total_leads': total_leads,
                'status_counts': status_counts,
                'source_counts': source_counts,
                'qualified_count': qualified_count,
                'unqualified_count': total_leads - qualified_count
            }
            
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {
                'total_leads': 0,
                'status_counts': {},
                'source_counts': {},
                'qualified_count': 0,
                'unqualified_count': 0
            }
    
    def _to_database_format(self, lead: UnifiedLead) -> Dict[str, Any]:
        """Convert UnifiedLead to database format"""
        return {
            'id': lead.id,
            'name': lead.name,
            'phone_number': lead.phone_number,
            'email': lead.email,
            'status': lead.status.value if hasattr(lead.status, 'value') else lead.status,
            'timezone': lead.timezone,
            'notes': lead.notes,
            'last_call_time': lead.last_call_time,
            'created_at': lead.created_at,
            'updated_at': lead.updated_at
        }
    
    def _from_database_format(self, data: Dict[str, Any]) -> UnifiedLead:
        """Convert database format to UnifiedLead"""
        return UnifiedLead(
            id=data.get('id'),
            name=data.get('name'),
            phone_number=data.get('phone_number'),
            email=data.get('email'),
            status=LeadStatus(data.get('status', 'new')),
            timezone=data.get('timezone', 'UTC'),
            notes=data.get('notes', ''),
            last_call_time=data.get('last_call_time'),
            created_at=data.get('created_at', datetime.utcnow()),
            updated_at=data.get('updated_at', datetime.utcnow()),
            source='call_system'  # Database leads are from call system
        )
    
    async def _save_to_backup(self, lead: UnifiedLead):
        """Save lead to backup file"""
        try:
            leads = await self._load_from_backup()
            leads.append(lead)
            
            # Convert to serializable format
            leads_data = [lead.dict() for lead in leads]
            
            with open(self.backup_file, 'w') as f:
                json.dump(leads_data, f, indent=2, default=str)
                
        except Exception as e:
            print(f"Error saving to backup: {e}")
    
    async def _load_from_backup(self) -> List[UnifiedLead]:
        """Load leads from backup file"""
        try:
            if not os.path.exists(self.backup_file):
                return []
                
            with open(self.backup_file, 'r') as f:
                leads_data = json.load(f)
                
            leads = []
            for lead_data in leads_data:
                try:
                    # Convert datetime strings back to datetime objects
                    if isinstance(lead_data.get('created_at'), str):
                        lead_data['created_at'] = datetime.fromisoformat(lead_data['created_at'])
                    if isinstance(lead_data.get('updated_at'), str):
                        lead_data['updated_at'] = datetime.fromisoformat(lead_data['updated_at'])
                    
                    lead = UnifiedLead(**lead_data)
                    leads.append(lead)
                except Exception as e:
                    print(f"Error loading lead from backup: {e}")
                    continue
                    
            return leads
            
        except Exception as e:
            print(f"Error loading from backup: {e}")
            return []
    
    async def _update_in_backup(self, updated_lead: UnifiedLead):
        """Update lead in backup file"""
        try:
            leads = await self._load_from_backup()
            
            # Find and update the lead
            for i, lead in enumerate(leads):
                if lead.id == updated_lead.id:
                    leads[i] = updated_lead
                    break
            
            # Save back to file
            leads_data = [lead.dict() for lead in leads]
            with open(self.backup_file, 'w') as f:
                json.dump(leads_data, f, indent=2, default=str)
                
        except Exception as e:
            print(f"Error updating backup: {e}")
    
    async def _remove_from_backup(self, lead_id: str):
        """Remove lead from backup file"""
        try:
            leads = await self._load_from_backup()
            leads = [lead for lead in leads if lead.id != lead_id]
            
            # Save back to file
            leads_data = [lead.dict() for lead in leads]
            with open(self.backup_file, 'w') as f:
                json.dump(leads_data, f, indent=2, default=str)
                
        except Exception as e:
            print(f"Error removing from backup: {e}")