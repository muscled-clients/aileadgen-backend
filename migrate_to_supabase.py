#!/usr/bin/env python3
"""
Migration script to move data from local JSON files to Supabase
"""

import json
import os
import asyncio
from datetime import datetime
from services.supabase_lead_service import SupabaseLeadService
from models.unified_lead import LeadCreateRequest

async def migrate_leads():
    """Migrate leads from JSON to Supabase"""
    print("🔄 Starting leads migration...")
    
    # Initialize Supabase service
    supabase_service = SupabaseLeadService()
    
    # Read existing leads from JSON file
    leads_file = os.path.join("database", "leads.json")
    if not os.path.exists(leads_file):
        print("❌ No leads.json file found")
        return
    
    try:
        with open(leads_file, 'r') as f:
            leads_data = json.load(f)
        
        print(f"📊 Found {len(leads_data)} leads to migrate")
        
        # Migrate each lead
        migrated_count = 0
        for lead_data in leads_data:
            try:
                # Parse name field if it exists (fallback to first_name/last_name if available)
                name_parts = lead_data.get('name', '').split(' ', 1) if lead_data.get('name') else ['', '']
                first_name = lead_data.get('first_name', name_parts[0] if name_parts else '')
                last_name = lead_data.get('last_name', name_parts[1] if len(name_parts) > 1 else '')
                
                # Handle phone number field variations
                phone = lead_data.get('phone', lead_data.get('phone_number', ''))
                
                # Create LeadCreateRequest from the data
                lead_request = LeadCreateRequest(
                    first_name=first_name,
                    last_name=last_name,
                    email=lead_data.get('email', ''),
                    phone=phone,
                    niche=lead_data.get('niche', ''),
                    is_serious=lead_data.get('is_serious', ''),
                    monthly_revenue=lead_data.get('monthly_revenue', ''),
                    pain_point=lead_data.get('pain_point', ''),
                    marketing_budget=lead_data.get('marketing_budget', ''),
                    qualified=lead_data.get('qualified', False),
                    completion_status=lead_data.get('completion_status', 'incomplete')
                )
                
                # Create lead in Supabase
                print(f"🔄 Migrating: {first_name} {last_name}")
                result = await supabase_service.create_lead(lead_request)
                if result:
                    migrated_count += 1
                    print(f"✅ Migrated lead: {first_name} {last_name}")
                else:
                    print(f"❌ Failed to migrate lead: {first_name} {last_name}")
                    
            except Exception as e:
                print(f"❌ Error migrating lead {lead_data.get('first_name', 'Unknown')}: {e}")
                continue
        
        print(f"🎉 Migration complete! {migrated_count}/{len(leads_data)} leads migrated successfully")
        
    except Exception as e:
        print(f"❌ Error reading leads file: {e}")

async def migrate_campaigns():
    """Migrate campaigns from JSON to Supabase"""
    print("🔄 Starting campaigns migration...")
    
    # Note: You'll need to create a SupabaseCampaignService similar to SupabaseLeadService
    # For now, let's just show what campaigns exist
    campaigns_file = os.path.join("database", "campaigns.json")
    if not os.path.exists(campaigns_file):
        print("❌ No campaigns.json file found")
        return
    
    try:
        with open(campaigns_file, 'r') as f:
            campaigns_data = json.load(f)
        
        print(f"📊 Found {len(campaigns_data)} campaigns to migrate")
        print("ℹ️  Campaign migration will be implemented after lead migration is complete")
        
        for campaign in campaigns_data:
            print(f"📋 Campaign: {campaign.get('name', 'Unknown')} - Status: {campaign.get('status', 'Unknown')}")
            
    except Exception as e:
        print(f"❌ Error reading campaigns file: {e}")

async def main():
    """Main migration function"""
    print("🚀 Starting data migration to Supabase...")
    print("=" * 50)
    
    # Migrate leads first
    await migrate_leads()
    
    print("\n" + "=" * 50)
    
    # Show campaigns (migration to be implemented)
    await migrate_campaigns()
    
    print("\n🎉 Migration process completed!")
    print("💡 You can now test your backend with Supabase data")

if __name__ == "__main__":
    asyncio.run(main())