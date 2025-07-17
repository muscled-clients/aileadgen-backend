"""
Campaign Service - File-based storage for campaigns
"""

import json
import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from models.campaign import Campaign, CampaignCreateRequest, CampaignUpdateRequest, CampaignStatus, CampaignStats

class CampaignService:
    """
    Campaign Service - uses local file storage
    Perfect for local development without external dependencies
    """
    
    def __init__(self):
        self.database_dir = "database"
        self.campaigns_file = os.path.join(self.database_dir, "campaigns.json")
        
        # Create database directory if it doesn't exist
        os.makedirs(self.database_dir, exist_ok=True)
        
        # Initialize campaigns file if it doesn't exist
        if not os.path.exists(self.campaigns_file):
            with open(self.campaigns_file, 'w') as f:
                json.dump([], f)
    
    def _load_campaigns(self) -> List[Dict]:
        """Load campaigns from file"""
        try:
            with open(self.campaigns_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _save_campaigns(self, campaigns: List[Dict]):
        """Save campaigns to file"""
        with open(self.campaigns_file, 'w') as f:
            json.dump(campaigns, f, indent=2)
    
    async def create_campaign(self, request: CampaignCreateRequest) -> Campaign:
        """Create a new campaign"""
        try:
            # Convert request to campaign
            campaign = request.to_campaign()
            
            # Set timestamps with timezone info
            now = datetime.now(timezone.utc).isoformat()
            campaign.created_at = now
            campaign.updated_at = now
            
            # Load existing campaigns
            campaigns = self._load_campaigns()
            
            # Add new campaign
            campaigns.append(campaign.dict())
            
            # Save campaigns
            self._save_campaigns(campaigns)
            
            return campaign
            
        except Exception as e:
            print(f"Error creating campaign: {e}")
            raise
    
    async def get_campaigns(self, skip: int = 0, limit: int = 100) -> List[Campaign]:
        """Get all campaigns sorted by newest first"""
        try:
            campaigns_data = self._load_campaigns()
            
            # Sort by created_at in descending order (newest first)
            campaigns_data.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # Apply pagination
            paginated_campaigns = campaigns_data[skip:skip + limit]
            
            # Convert to Campaign objects
            campaigns = []
            for campaign_data in paginated_campaigns:
                try:
                    campaign = Campaign(**campaign_data)
                    campaigns.append(campaign)
                except Exception as e:
                    print(f"Error parsing campaign {campaign_data.get('id', 'unknown')}: {e}")
                    continue
            
            return campaigns
            
        except Exception as e:
            print(f"Error getting campaigns: {e}")
            return []
    
    async def get_campaign_by_id(self, campaign_id: str) -> Optional[Campaign]:
        """Get a specific campaign by ID"""
        try:
            campaigns_data = self._load_campaigns()
            
            for campaign_data in campaigns_data:
                if campaign_data.get('id') == campaign_id:
                    return Campaign(**campaign_data)
            
            return None
            
        except Exception as e:
            print(f"Error getting campaign by ID: {e}")
            return None
    
    async def update_campaign(self, campaign_id: str, request: CampaignUpdateRequest) -> Optional[Campaign]:
        """Update an existing campaign"""
        try:
            campaigns_data = self._load_campaigns()
            
            for i, campaign_data in enumerate(campaigns_data):
                if campaign_data.get('id') == campaign_id:
                    # Update fields
                    update_data = request.dict(exclude_unset=True)
                    campaign_data.update(update_data)
                    campaign_data['updated_at'] = datetime.now(timezone.utc).isoformat()
                    
                    # Save campaigns
                    self._save_campaigns(campaigns_data)
                    
                    return Campaign(**campaign_data)
            
            return None
            
        except Exception as e:
            print(f"Error updating campaign: {e}")
            return None
    
    async def delete_campaign(self, campaign_id: str) -> bool:
        """Delete a campaign"""
        try:
            campaigns_data = self._load_campaigns()
            
            for i, campaign_data in enumerate(campaigns_data):
                if campaign_data.get('id') == campaign_id:
                    del campaigns_data[i]
                    self._save_campaigns(campaigns_data)
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error deleting campaign: {e}")
            return False
    
    async def start_campaign(self, campaign_id: str) -> Optional[Campaign]:
        """Start a campaign"""
        try:
            campaigns_data = self._load_campaigns()
            
            for campaign_data in campaigns_data:
                if campaign_data.get('id') == campaign_id:
                    campaign_data['status'] = CampaignStatus.RUNNING
                    campaign_data['started_at'] = datetime.now(timezone.utc).isoformat()
                    campaign_data['updated_at'] = datetime.now(timezone.utc).isoformat()
                    
                    self._save_campaigns(campaigns_data)
                    return Campaign(**campaign_data)
            
            return None
            
        except Exception as e:
            print(f"Error starting campaign: {e}")
            return None
    
    async def pause_campaign(self, campaign_id: str) -> Optional[Campaign]:
        """Pause a campaign"""
        try:
            campaigns_data = self._load_campaigns()
            
            for campaign_data in campaigns_data:
                if campaign_data.get('id') == campaign_id:
                    campaign_data['status'] = CampaignStatus.PAUSED
                    campaign_data['updated_at'] = datetime.now(timezone.utc).isoformat()
                    
                    self._save_campaigns(campaigns_data)
                    return Campaign(**campaign_data)
            
            return None
            
        except Exception as e:
            print(f"Error pausing campaign: {e}")
            return None
    
    async def resume_campaign(self, campaign_id: str) -> Optional[Campaign]:
        """Resume a paused campaign"""
        try:
            campaigns_data = self._load_campaigns()
            
            for campaign_data in campaigns_data:
                if campaign_data.get('id') == campaign_id:
                    campaign_data['status'] = CampaignStatus.RUNNING
                    campaign_data['updated_at'] = datetime.now(timezone.utc).isoformat()
                    
                    self._save_campaigns(campaigns_data)
                    return Campaign(**campaign_data)
            
            return None
            
        except Exception as e:
            print(f"Error resuming campaign: {e}")
            return None
    
    async def get_campaign_stats(self) -> CampaignStats:
        """Get campaign statistics"""
        try:
            campaigns_data = self._load_campaigns()
            
            total_campaigns = len(campaigns_data)
            active_campaigns = 0
            completed_campaigns = 0
            total_leads_in_campaigns = 0
            total_calls_made = 0
            successful_calls = 0
            
            for campaign_data in campaigns_data:
                status = campaign_data.get('status', 'created')
                if status in ['running', 'paused']:
                    active_campaigns += 1
                elif status == 'completed':
                    completed_campaigns += 1
                
                total_leads_in_campaigns += campaign_data.get('total_leads', 0)
                calls_made = campaign_data.get('called_leads', 0)
                total_calls_made += calls_made
                successful_calls += campaign_data.get('successful_calls', 0)
            
            # Calculate success rate
            success_rate = (successful_calls / total_calls_made * 100) if total_calls_made > 0 else 0.0
            
            return CampaignStats(
                total_campaigns=total_campaigns,
                active_campaigns=active_campaigns,
                completed_campaigns=completed_campaigns,
                total_leads_in_campaigns=total_leads_in_campaigns,
                total_calls_made=total_calls_made,
                success_rate=round(success_rate, 2)
            )
            
        except Exception as e:
            print(f"Error getting campaign stats: {e}")
            return CampaignStats()