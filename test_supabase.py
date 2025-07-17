#!/usr/bin/env python3
"""
Simple test script to debug Supabase connection
"""

import asyncio
from services.supabase_lead_service import SupabaseLeadService
from models.unified_lead import LeadCreateRequest

async def test_supabase():
    print("🔧 Testing Supabase connection...")
    
    # Initialize service
    service = SupabaseLeadService()
    
    # Create a simple test lead
    test_lead = LeadCreateRequest(
        first_name="Test",
        last_name="Migration",
        email="test@migration.com",
        phone="1234567890",
        niche="real-estate"
    )
    
    print(f"📤 Creating test lead: {test_lead.first_name} {test_lead.last_name}")
    
    try:
        result = await service.create_lead(test_lead)
        if result:
            print(f"✅ Success! Created lead with ID: {result.id}")
        else:
            print("❌ Failed to create lead - no result returned")
    except Exception as e:
        print(f"❌ Error creating lead: {e}")
    
    # Test fetching leads
    print("\n📥 Testing lead retrieval...")
    try:
        leads = await service.get_leads(limit=5)
        print(f"✅ Retrieved {len(leads)} leads")
        for lead in leads:
            print(f"  - {lead.first_name} {lead.last_name} ({lead.email})")
    except Exception as e:
        print(f"❌ Error retrieving leads: {e}")

if __name__ == "__main__":
    asyncio.run(test_supabase())