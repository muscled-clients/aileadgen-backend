"""
AI Lead Gen Backend - Optimized and Clean
FastAPI application with proper error handling, validation, and unified data storage
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
import asyncio
import json
import os
from typing import Dict, List, Optional
from datetime import datetime
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import unified models and services
from models.unified_lead import UnifiedLead, LeadCreateRequest, LeadUpdateRequest
from services.unified_lead_service import UnifiedLeadService
from services.retell_service import RetellService

# Initialize FastAPI app
app = FastAPI(
    title="AI Lead Gen API",
    description="Unified API for lead management and AI calling",
    version="2.0.0"
)

# Configure CORS - More restrictive than before
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# Initialize services
lead_service = UnifiedLeadService()
retell_service = RetellService()

# Store active calls (keeping this for real-time functionality)
active_calls: Dict[str, dict] = {}

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# === UNIFIED LEAD ENDPOINTS ===

@app.post("/api/leads", response_model=UnifiedLead)
async def create_lead(request: LeadCreateRequest):
    """
    Create a new lead with proper validation
    Handles both landing page and call system leads
    """
    try:
        lead = await lead_service.create_lead(request)
        return lead
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/leads", response_model=List[UnifiedLead])
async def get_leads(skip: int = 0, limit: int = 100):
    """
    Get all leads with pagination
    """
    try:
        if skip < 0 or limit < 1 or limit > 1000:
            raise HTTPException(status_code=400, detail="Invalid pagination parameters")
        
        leads = await lead_service.get_leads(skip, limit)
        return leads
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/leads/{lead_id}", response_model=UnifiedLead)
async def get_lead(lead_id: str):
    """
    Get a specific lead by ID
    """
    try:
        lead = await lead_service.get_lead_by_id(lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        return lead
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.put("/api/leads/{lead_id}", response_model=UnifiedLead)
async def update_lead(lead_id: str, request: LeadUpdateRequest):
    """
    Update an existing lead
    """
    try:
        lead = await lead_service.update_lead(lead_id, request)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        return lead
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.delete("/api/leads/{lead_id}")
async def delete_lead(lead_id: str):
    """
    Delete a lead
    """
    try:
        success = await lead_service.delete_lead(lead_id)
        if not success:
            raise HTTPException(status_code=404, detail="Lead not found")
        return {"message": "Lead deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/leads/stats")
async def get_lead_stats():
    """
    Get lead statistics
    """
    try:
        stats = await lead_service.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# === DASHBOARD ENDPOINTS ===

@app.get("/dashboard/stats")
async def get_dashboard_stats():
    """
    Get dashboard statistics - unified from all data sources
    """
    try:
        # Get lead stats
        lead_stats = await lead_service.get_stats()
        
        # Get call stats (if available)
        call_stats = {
            'total_calls': 0,
            'todays_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'average_duration': 0
        }
        
        # Combine stats
        return {
            "totalLeads": lead_stats.get('total_leads', 0),
            "newLeads": lead_stats.get('status_counts', {}).get('new', 0),
            "calledLeads": lead_stats.get('status_counts', {}).get('called', 0),
            "bookedLeads": lead_stats.get('status_counts', {}).get('booked', 0),
            "callbackLeads": lead_stats.get('status_counts', {}).get('callback', 0),
            "notAnsweredLeads": lead_stats.get('status_counts', {}).get('not_answered', 0),
            "failedLeads": lead_stats.get('status_counts', {}).get('failed', 0),
            "qualifiedLeads": lead_stats.get('qualified_count', 0),
            "unqualifiedLeads": lead_stats.get('unqualified_count', 0),
            "totalCalls": call_stats['total_calls'],
            "todaysCalls": call_stats['todays_calls'],
            "successfulCalls": call_stats['successful_calls'],
            "failedCalls": call_stats['failed_calls'],
            "averageDuration": call_stats['average_duration']
        }
    except Exception as e:
        print(f"Error fetching dashboard stats: {e}")
        # Return safe defaults
        return {
            "totalLeads": 0,
            "newLeads": 0,
            "calledLeads": 0,
            "bookedLeads": 0,
            "callbackLeads": 0,
            "notAnsweredLeads": 0,
            "failedLeads": 0,
            "qualifiedLeads": 0,
            "unqualifiedLeads": 0,
            "totalCalls": 0,
            "todaysCalls": 0,
            "successfulCalls": 0,
            "failedCalls": 0,
            "averageDuration": 0
        }

# === CALL MANAGEMENT ENDPOINTS ===

@app.post("/api/calls/initiate")
async def initiate_call(request: dict):
    """
    Initiate a call using Retell.ai
    """
    try:
        lead_id = request.get("lead_id")
        if not lead_id:
            raise HTTPException(status_code=400, detail="lead_id is required")
        
        # Get lead info
        lead = await lead_service.get_lead_by_id(lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        # Use environment variable for agent ID
        agent_id = os.getenv("RETELL_AGENT_ID", "agent_553d0e0440b066f74330089aec")
        
        # Create the call
        call_result = await retell_service.create_phone_call(lead.phone_number, agent_id)
        
        if "error" in call_result:
            raise HTTPException(status_code=400, detail=call_result["error"])
        
        call_id = call_result.get("call_id")
        
        # Store call info
        active_calls[call_id] = {
            "lead_id": lead_id,
            "phone_number": lead.phone_number,
            "service": "retell",
            "agent_id": agent_id,
            "status": "initiated",
            "start_time": datetime.now(),
            "transcript": []
        }
        
        return {
            "success": True,
            "call_id": call_id,
            "lead_id": lead_id,
            "message": f"Call initiated to {lead.phone_number}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/calls/active")
async def get_active_calls():
    """
    Get all active calls
    """
    try:
        return {"active_calls": active_calls}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/calls/{call_id}/end")
async def end_call(call_id: str):
    """
    End an active call
    """
    try:
        if call_id not in active_calls:
            raise HTTPException(status_code=404, detail="Call not found")
        
        active_calls[call_id]["status"] = "completed"
        active_calls[call_id]["end_time"] = datetime.now()
        
        return {"message": "Call ended successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# === WEBHOOK ENDPOINTS ===

@app.post("/webhooks/retell/call-status")
async def handle_retell_webhook(request: Request):
    """
    Handle Retell.ai webhook for call status updates
    """
    try:
        body = await request.json()
        call_id = body.get("call_id")
        event = body.get("event")
        
        if call_id and call_id in active_calls:
            if event == "call_ended":
                active_calls[call_id]["status"] = "completed"
                active_calls[call_id]["end_time"] = datetime.now()
            elif event == "call_started":
                active_calls[call_id]["status"] = "in-progress"
        
        return {"status": "ok"}
    except Exception as e:
        print(f"Error handling Retell webhook: {e}")
        return {"status": "error", "message": str(e)}

# === ERROR HANDLERS ===

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors"""
    return JSONResponse(
        status_code=400,
        content={"detail": f"Validation error: {str(exc)}"}
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle value errors"""
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    print(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# === STARTUP/SHUTDOWN EVENTS ===

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    print("🚀 AI Lead Gen API starting up...")
    print(f"✅ Services initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("👋 AI Lead Gen API shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)