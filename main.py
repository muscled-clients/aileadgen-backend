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
import time

# Import logging utilities
from utils.logger import logger, log_api_request, log_business_event, log_validation_error, RequestContext

# Load environment variables
load_dotenv()

# Import unified models and services
from models.unified_lead import UnifiedLead, LeadCreateRequest, LeadUpdateRequest
from models.campaign import Campaign, CampaignCreateRequest, CampaignUpdateRequest, CampaignStatus
from services.simple_lead_service import SimpleLeadService
from services.supabase_lead_service import SupabaseLeadService
from services.campaign_service import CampaignService
from services.retell_service import RetellService
from services.email_service import EmailService, EmailTemplate, EmailSendRequest, EmailSendResult
from services.email_lead_service import EmailLeadService
from services.workflow_service import WorkflowService, EmailWorkflow
from services.lead_segmentation_service import LeadSegmentationService
from services.email_compliance_service import EmailComplianceService
from services.bounce_handling_service import BounceHandlingService

# Initialize FastAPI app
app = FastAPI(
    title="AI Lead Gen API",
    description="Unified API for lead management and AI calling",
    version="2.0.0"
)

# Configure CORS - Allow localhost and production domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:3001",
        "https://aileadgen-frontend.vercel.app",
        "https://aileadgen.dev",
        "https://www.aileadgen.dev"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# Initialize services
# Use Supabase for production, SimpleLeadService for development
use_supabase = os.getenv("USE_SUPABASE", "true").lower() == "true"
lead_service = SupabaseLeadService() if use_supabase else SimpleLeadService()
campaign_service = CampaignService()
retell_service = RetellService()
email_service = EmailService()
email_lead_service = EmailLeadService()
workflow_service = WorkflowService()
segmentation_service = LeadSegmentationService()
compliance_service = EmailComplianceService()
bounce_service = BounceHandlingService()

# Store active calls (keeping this for real-time functionality)
active_calls: Dict[str, dict] = {}

# Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log all HTTP requests"""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # Extract user ID from request if available (e.g., from JWT token)
    user_id = request.headers.get("X-User-ID")
    
    with RequestContext(request_id, user_id):
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            user_agent=request.headers.get("user-agent"),
            remote_addr=request.client.host if request.client else None
        )
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            log_api_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=duration,
                user_id=user_id
            )
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                error=e,
                duration=duration
            )
            
            raise

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
        logger.info("Creating new lead", lead_data=request.dict())
        lead = await lead_service.create_lead(request)
        
        log_business_event(
            event="lead_created",
            entity_type="lead",
            entity_id=lead.id,
            details={
                "source": lead.source,
                "qualified": lead.qualified,
                "email": lead.email,
                "phone": lead.phone_number
            }
        )
        
        logger.info(f"Lead created successfully: {lead.id}")
        
        # Trigger welcome email automation if lead is complete
        if lead.completion_status == "complete":
            try:
                await email_lead_service.trigger_lead_workflow(lead.id, "new_lead")
                logger.info(f"Welcome email triggered for new lead: {lead.id}")
            except Exception as e:
                logger.error(f"Failed to trigger welcome email for new lead: {e}")
                # Don't fail the lead creation if email fails
        
        return lead
        
    except ValidationError as e:
        log_validation_error("lead_creation", request.dict(), str(e))
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    except ValueError as e:
        logger.error(f"Invalid lead data: {str(e)}", lead_data=request.dict())
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create lead: {str(e)}", error=e, lead_data=request.dict())
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

@app.patch("/api/leads/{lead_id}", response_model=UnifiedLead)
async def patch_lead(lead_id: str, request: LeadUpdateRequest):
    """
    Partially update an existing lead (for progressive form updates)
    """
    try:
        logger.info(f"Patching lead {lead_id}", lead_data=request.dict(exclude_none=True))
        
        lead = await lead_service.update_lead(lead_id, request)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        log_business_event(
            event="lead_updated",
            entity_type="lead",
            entity_id=lead.id,
            details={
                "completion_status": lead.completion_status,
                "updated_fields": [k for k, v in request.dict(exclude_none=True).items() if v is not None]
            }
        )
        
        logger.info(f"Lead patched successfully: {lead_id}")
        
        # Trigger qualification email if lead becomes qualified
        if lead.qualified and lead.completion_status == "complete":
            try:
                # Check if this is a new qualification
                original_lead = await lead_service.get_lead_by_id(lead_id)
                if original_lead and not original_lead.qualified:
                    await email_lead_service.trigger_lead_workflow(lead_id, "qualified")
                    logger.info(f"Qualification email triggered for lead: {lead_id}")
            except Exception as e:
                logger.error(f"Failed to trigger qualification email: {e}")
                # Don't fail the lead update if email fails
        
        return lead
        
    except ValidationError as e:
        log_validation_error("lead_update", request.dict(), str(e))
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    except ValueError as e:
        logger.error(f"Invalid lead update data: {str(e)}", lead_data=request.dict())
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to patch lead: {str(e)}", error=e, lead_data=request.dict())
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

# === CAMPAIGN ENDPOINTS ===

@app.post("/api/campaigns", response_model=Campaign)
async def create_campaign(request: CampaignCreateRequest):
    """
    Create a new campaign
    """
    try:
        logger.info("Campaign creation requested", extra={"lead_count": len(request.lead_ids)})
        
        # Validate that lead IDs exist
        for lead_id in request.lead_ids:
            lead = await lead_service.get_lead_by_id(lead_id)
            if not lead:
                raise HTTPException(status_code=400, detail=f"Lead with ID {lead_id} not found")
        
        # Create campaign
        campaign = await campaign_service.create_campaign(request)
        
        logger.info("Campaign created", extra={"campaign_id": campaign.id, "lead_count": campaign.total_leads})
        logger.info(f"Campaign created successfully: {campaign.id}")
        
        return campaign
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating campaign: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/campaigns", response_model=List[Campaign])
async def get_campaigns(skip: int = 0, limit: int = 100):
    """
    Get all campaigns
    """
    try:
        campaigns = await campaign_service.get_campaigns(skip=skip, limit=limit)
        return campaigns
    except Exception as e:
        logger.error(f"Error getting campaigns: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/campaigns/{campaign_id}", response_model=Campaign)
async def get_campaign(campaign_id: str):
    """
    Get a specific campaign by ID
    """
    try:
        campaign = await campaign_service.get_campaign_by_id(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return campaign
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.put("/api/campaigns/{campaign_id}", response_model=Campaign)
async def update_campaign(campaign_id: str, request: CampaignUpdateRequest):
    """
    Update an existing campaign
    """
    try:
        campaign = await campaign_service.update_campaign(campaign_id, request)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        logger.info("Campaign updated", extra={"campaign_id": campaign_id})
        logger.info(f"Campaign updated successfully: {campaign_id}")
        
        return campaign
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating campaign: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.delete("/api/campaigns/{campaign_id}")
async def delete_campaign(campaign_id: str):
    """
    Delete a campaign
    """
    try:
        success = await campaign_service.delete_campaign(campaign_id)
        if not success:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        logger.info("Campaign deleted", extra={"campaign_id": campaign_id})
        logger.info(f"Campaign deleted successfully: {campaign_id}")
        
        return {"message": "Campaign deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting campaign: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/campaigns/{campaign_id}/start", response_model=Campaign)
async def start_campaign(campaign_id: str):
    """
    Start a campaign
    """
    try:
        campaign = await campaign_service.start_campaign(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        logger.info("Campaign started", extra={"campaign_id": campaign_id})
        logger.info(f"Campaign started successfully: {campaign_id}")
        
        return campaign
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting campaign: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/campaigns/{campaign_id}/pause", response_model=Campaign)
async def pause_campaign(campaign_id: str):
    """
    Pause a campaign
    """
    try:
        campaign = await campaign_service.pause_campaign(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        logger.info("Campaign paused", extra={"campaign_id": campaign_id})
        logger.info(f"Campaign paused successfully: {campaign_id}")
        
        return campaign
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing campaign: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/campaigns/{campaign_id}/resume", response_model=Campaign)
async def resume_campaign(campaign_id: str):
    """
    Resume a paused campaign
    """
    try:
        campaign = await campaign_service.resume_campaign(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        logger.info("Campaign resumed", extra={"campaign_id": campaign_id})
        logger.info(f"Campaign resumed successfully: {campaign_id}")
        
        return campaign
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming campaign: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/campaigns/stats")
async def get_campaign_stats():
    """
    Get campaign statistics
    """
    try:
        stats = await campaign_service.get_campaign_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting campaign stats: {e}")
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

# === EMAIL AUTOMATION ENDPOINTS ===

@app.get("/api/email-automation/templates", response_model=List[EmailTemplate])
async def get_email_templates():
    """
    Get all email templates
    """
    try:
        templates = email_service._load_templates()
        return templates
    except Exception as e:
        logger.error(f"Error getting email templates: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/email-automation/templates", response_model=EmailTemplate)
async def create_email_template(template_data: dict):
    """
    Create a new email template
    """
    try:
        template = await email_service.create_template(template_data)
        return template
    except Exception as e:
        logger.error(f"Error creating email template: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/email-automation/templates/{template_id}", response_model=EmailTemplate)
async def get_email_template(template_id: str):
    """
    Get a specific email template
    """
    try:
        template = await email_service.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        return template
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting email template: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.put("/api/email-automation/templates/{template_id}", response_model=EmailTemplate)
async def update_email_template(template_id: str, template_data: dict):
    """
    Update an existing email template
    """
    try:
        template = await email_service.update_template(template_id, template_data)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        return template
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating email template: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.delete("/api/email-automation/templates/{template_id}")
async def delete_email_template(template_id: str):
    """
    Delete an email template
    """
    try:
        success = await email_service.delete_template(template_id)
        if not success:
            raise HTTPException(status_code=404, detail="Template not found")
        return {"message": "Template deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting email template: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/email-automation/send", response_model=EmailSendResult)
async def send_email(email_request: EmailSendRequest):
    """
    Send an email using the email service
    """
    try:
        result = await email_service.send_email(email_request)
        return result
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/email-automation/send-test", response_model=EmailSendResult)
async def send_test_email(request: dict):
    """
    Send a test email with a specific template
    """
    try:
        to_email = request.get("to_email")
        template_id = request.get("template_id")
        variables = request.get("variables", {})
        
        if not to_email or not template_id:
            raise HTTPException(status_code=400, detail="to_email and template_id are required")
        
        result = await email_service.send_test_email(to_email, template_id, variables)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending test email: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/email-automation/history")
async def get_email_history(limit: int = 100, offset: int = 0):
    """
    Get email history with pagination
    """
    try:
        history = await email_service.get_email_history(limit, offset)
        return {"emails": history}
    except Exception as e:
        logger.error(f"Error getting email history: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/email-automation/history/workflow/{workflow_id}")
async def get_email_history_by_workflow(workflow_id: str):
    """
    Get email history for a specific workflow
    """
    try:
        history = await email_service.get_email_history_by_workflow(workflow_id)
        return {"emails": history}
    except Exception as e:
        logger.error(f"Error getting email history by workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/email-automation/history/lead/{lead_id}")
async def get_email_history_by_lead(lead_id: str):
    """
    Get email history for a specific lead
    """
    try:
        history = await email_service.get_email_history_by_lead(lead_id)
        return {"emails": history}
    except Exception as e:
        logger.error(f"Error getting email history by lead: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/email-automation/webhook/status")
async def handle_email_webhook(request: Request):
    """
    Handle email service webhooks (from Resend)
    """
    try:
        body = await request.json()
        event_type = body.get("type")
        email_id = body.get("data", {}).get("email_id")
        
        if event_type and email_id:
            status_mapping = {
                "email.delivered": "delivered",
                "email.opened": "opened",
                "email.clicked": "clicked",
                "email.bounced": "bounced",
                "email.complained": "failed"
            }
            
            new_status = status_mapping.get(event_type)
            if new_status:
                await email_service.update_email_status(email_id, new_status)
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error handling email webhook: {e}")
        return {"status": "error", "message": str(e)}

# === EMAIL WORKFLOWS ===

@app.get("/api/email-automation/workflows", response_model=List[EmailWorkflow])
async def get_email_workflows(trigger_type: str = None, status: str = None):
    """
    Get all email workflows with optional filtering
    """
    try:
        workflows = await workflow_service.get_workflows(trigger_type, status)
        return workflows
    except Exception as e:
        logger.error(f"Error getting email workflows: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/email-automation/workflows", response_model=EmailWorkflow)
async def create_email_workflow(workflow_data: dict):
    """
    Create a new email workflow
    """
    try:
        workflow = await workflow_service.create_workflow(workflow_data)
        return workflow
    except Exception as e:
        logger.error(f"Error creating email workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/email-automation/workflows/{workflow_id}", response_model=EmailWorkflow)
async def get_email_workflow(workflow_id: str):
    """
    Get a specific email workflow
    """
    try:
        workflow = await workflow_service.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return workflow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting email workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.put("/api/email-automation/workflows/{workflow_id}", response_model=EmailWorkflow)
async def update_email_workflow(workflow_id: str, workflow_data: dict):
    """
    Update an existing email workflow
    """
    try:
        workflow = await workflow_service.update_workflow(workflow_id, workflow_data)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return workflow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating email workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.delete("/api/email-automation/workflows/{workflow_id}")
async def delete_email_workflow(workflow_id: str):
    """
    Delete an email workflow
    """
    try:
        success = await workflow_service.delete_workflow(workflow_id)
        if not success:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return {"message": "Workflow deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting email workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/email-automation/workflows/{workflow_id}/pause", response_model=EmailWorkflow)
async def pause_email_workflow(workflow_id: str):
    """
    Pause an email workflow
    """
    try:
        workflow = await workflow_service.pause_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return workflow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing email workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/email-automation/workflows/{workflow_id}/activate", response_model=EmailWorkflow)
async def activate_email_workflow(workflow_id: str):
    """
    Activate an email workflow
    """
    try:
        workflow = await workflow_service.activate_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return workflow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating email workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/email-automation/workflows/{workflow_id}/trigger")
async def trigger_email_workflow(workflow_id: str, request: dict):
    """
    Trigger an email workflow for a specific lead
    """
    try:
        lead_id = request.get("lead_id")
        if not lead_id:
            raise HTTPException(status_code=400, detail="lead_id is required")
        
        success = await workflow_service.trigger_workflow(workflow_id, lead_id)
        if success:
            return {"message": "Workflow triggered successfully", "workflow_id": workflow_id, "lead_id": lead_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to trigger workflow")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering email workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/email-automation/workflows/stats")
async def get_workflow_stats():
    """
    Get workflow statistics
    """
    try:
        stats = await workflow_service.get_workflow_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting workflow stats: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/email-automation/workflows/executions/pending")
async def get_pending_workflow_executions():
    """
    Get pending workflow executions
    """
    try:
        executions = await workflow_service.get_pending_executions()
        return {"executions": [execution.dict() for execution in executions]}
    except Exception as e:
        logger.error(f"Error getting pending executions: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/email-automation/workflows/executions/lead/{lead_id}")
async def get_lead_workflow_executions(lead_id: str):
    """
    Get all workflow executions for a specific lead
    """
    try:
        executions = await workflow_service.get_lead_workflow_executions(lead_id)
        return {"executions": [execution.dict() for execution in executions]}
    except Exception as e:
        logger.error(f"Error getting lead workflow executions: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# === EMAIL LEAD INTEGRATION ===

@app.post("/api/email-automation/leads/{lead_id}/welcome")
async def send_welcome_email_to_lead(lead_id: str):
    """
    Send welcome email to a specific lead
    """
    try:
        success = await email_lead_service.send_welcome_email(lead_id)
        if success:
            return {"message": "Welcome email sent successfully", "lead_id": lead_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to send welcome email")
    except Exception as e:
        logger.error(f"Error sending welcome email to lead: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/email-automation/leads/{lead_id}/qualification")
async def send_qualification_email_to_lead(lead_id: str):
    """
    Send qualification email to a specific lead
    """
    try:
        success = await email_lead_service.send_qualification_email(lead_id)
        if success:
            return {"message": "Qualification email sent successfully", "lead_id": lead_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to send qualification email")
    except Exception as e:
        logger.error(f"Error sending qualification email to lead: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/email-automation/leads/{lead_id}/follow-up")
async def send_follow_up_email_to_lead(lead_id: str, follow_up_type: str = "general"):
    """
    Send follow-up email to a specific lead
    """
    try:
        success = await email_lead_service.send_follow_up_email(lead_id, follow_up_type)
        if success:
            return {"message": "Follow-up email sent successfully", "lead_id": lead_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to send follow-up email")
    except Exception as e:
        logger.error(f"Error sending follow-up email to lead: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/email-automation/leads/{lead_id}/process")
async def process_lead_for_automation(lead_id: str):
    """
    Process a lead for email automation based on their current status
    """
    try:
        result = await email_lead_service.process_lead_for_automation(lead_id)
        return result
    except Exception as e:
        logger.error(f"Error processing lead for automation: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/email-automation/leads/bulk-process")
async def bulk_process_leads_for_automation(request: dict):
    """
    Process multiple leads for email automation
    """
    try:
        lead_ids = request.get("lead_ids", [])
        if not lead_ids:
            raise HTTPException(status_code=400, detail="lead_ids array is required")
        
        result = await email_lead_service.bulk_process_leads(lead_ids)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk processing leads: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/email-automation/triggers/{trigger_type}")
async def trigger_email_automation(trigger_type: str, request: dict):
    """
    Trigger email automation based on events (new lead, qualified, etc.)
    """
    try:
        lead_id = request.get("lead_id")
        if not lead_id:
            raise HTTPException(status_code=400, detail="lead_id is required")
        
        success = await email_lead_service.trigger_lead_workflow(lead_id, trigger_type)
        if success:
            return {"message": f"Email automation triggered: {trigger_type}", "lead_id": lead_id}
        else:
            raise HTTPException(status_code=400, detail=f"Failed to trigger automation: {trigger_type}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering email automation: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# === LEAD SEGMENTATION ===

@app.get("/api/email-automation/segments")
async def get_available_segments():
    """
    Get all available lead segments
    """
    try:
        segments = await segmentation_service.get_available_segments()
        return {"segments": segments}
    except Exception as e:
        logger.error(f"Error getting available segments: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/email-automation/segments/{segment_name}/leads")
async def get_leads_by_segment(segment_name: str):
    """
    Get all leads that match a specific segment
    """
    try:
        leads = await segmentation_service.get_leads_by_segment(segment_name)
        return {"leads": leads, "count": len(leads)}
    except Exception as e:
        logger.error(f"Error getting leads by segment: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/email-automation/segments/{segment_name}/stats")
async def get_segment_stats(segment_name: str):
    """
    Get statistics for a specific segment
    """
    try:
        stats = await segmentation_service.get_segment_stats(segment_name)
        return {"segment": segment_name, "stats": stats}
    except Exception as e:
        logger.error(f"Error getting segment stats: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/email-automation/segments/preview")
async def preview_segment(criteria: dict):
    """
    Preview how many leads would match given criteria
    """
    try:
        preview = await segmentation_service.get_segment_preview(criteria)
        return {"preview": preview}
    except Exception as e:
        logger.error(f"Error previewing segment: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/email-automation/segments/custom")
async def create_custom_segment(request: dict):
    """
    Create a custom segment with specific criteria
    """
    try:
        name = request.get("name")
        criteria = request.get("criteria", {})
        
        if not name:
            raise HTTPException(status_code=400, detail="Segment name is required")
        
        segment = await segmentation_service.create_custom_segment(name, criteria)
        return {"segment": {"name": segment.name, "criteria": segment.criteria}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating custom segment: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/email-automation/segments/{segment_name}/performance")
async def get_segment_performance(segment_name: str):
    """
    Get email performance analytics for a specific segment
    """
    try:
        performance = await segmentation_service.analyze_segment_performance(segment_name)
        return {"performance": performance}
    except Exception as e:
        logger.error(f"Error getting segment performance: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# === EMAIL COMPLIANCE ===

@app.post("/api/email-automation/unsubscribe")
async def unsubscribe_email(request: dict):
    """
    Unsubscribe an email address from all communications
    """
    try:
        email = request.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
        
        reason = request.get("reason")
        source = request.get("source", "email_link")
        workflow_id = request.get("workflow_id")
        template_id = request.get("template_id")
        
        success = await compliance_service.unsubscribe_email(
            email=email,
            reason=reason,
            source=source,
            workflow_id=workflow_id,
            template_id=template_id
        )
        
        if success:
            return {"message": "Email unsubscribed successfully", "email": email}
        else:
            raise HTTPException(status_code=400, detail="Failed to unsubscribe email")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unsubscribing email: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/email-automation/unsubscribe/token")
async def unsubscribe_with_token(request: dict):
    """
    Unsubscribe using a secure token
    """
    try:
        token = request.get("token")
        if not token:
            raise HTTPException(status_code=400, detail="Token is required")
        
        # Verify token
        token_data = await compliance_service.verify_unsubscribe_token(token)
        if not token_data:
            raise HTTPException(status_code=400, detail="Invalid or expired token")
        
        email = token_data["email"]
        reason = request.get("reason")
        workflow_id = request.get("workflow_id")
        template_id = request.get("template_id")
        
        success = await compliance_service.unsubscribe_email(
            email=email,
            reason=reason,
            source="email_link",
            workflow_id=workflow_id,
            template_id=template_id
        )
        
        if success:
            return {"message": "Email unsubscribed successfully", "email": email}
        else:
            raise HTTPException(status_code=400, detail="Failed to unsubscribe email")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unsubscribing with token: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/email-automation/suppression-list")
async def get_suppression_list(limit: int = 100, offset: int = 0):
    """
    Get the current suppression list
    """
    try:
        suppression_list = await compliance_service.get_suppression_list(limit, offset)
        return {"suppression_list": suppression_list}
    except Exception as e:
        logger.error(f"Error getting suppression list: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/email-automation/suppression-list/add")
async def add_to_suppression_list(request: dict):
    """
    Add an email to the suppression list
    """
    try:
        email = request.get("email")
        reason = request.get("reason", "manual")
        source = request.get("source", "manual")
        
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
        
        success = await compliance_service.add_to_suppression_list(email, reason, source)
        
        if success:
            return {"message": "Email added to suppression list", "email": email}
        else:
            raise HTTPException(status_code=400, detail="Failed to add email to suppression list")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding to suppression list: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.delete("/api/email-automation/suppression-list/{email}")
async def remove_from_suppression_list(email: str):
    """
    Remove an email from the suppression list (resubscribe)
    """
    try:
        success = await compliance_service.remove_from_suppression_list(email)
        
        if success:
            return {"message": "Email removed from suppression list", "email": email}
        else:
            raise HTTPException(status_code=404, detail="Email not found in suppression list")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing from suppression list: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/email-automation/compliance/stats")
async def get_compliance_stats():
    """
    Get email compliance statistics
    """
    try:
        stats = await compliance_service.get_compliance_stats()
        return {"stats": stats}
    except Exception as e:
        logger.error(f"Error getting compliance stats: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/email-automation/compliance/check/{email}")
async def check_email_suppression(email: str):
    """
    Check if an email is suppressed
    """
    try:
        is_suppressed = await compliance_service.is_email_suppressed(email)
        reason = await compliance_service.get_suppression_reason(email) if is_suppressed else None
        
        return {
            "email": email,
            "is_suppressed": is_suppressed,
            "reason": reason
        }
    except Exception as e:
        logger.error(f"Error checking email suppression: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/email-automation/compliance/filter")
async def filter_suppressed_emails(request: dict):
    """
    Filter out suppressed emails from a list
    """
    try:
        email_list = request.get("emails", [])
        if not email_list:
            raise HTTPException(status_code=400, detail="Email list is required")
        
        filtered_emails = await compliance_service.filter_suppressed_emails(email_list)
        
        return {
            "original_count": len(email_list),
            "filtered_count": len(filtered_emails),
            "removed_count": len(email_list) - len(filtered_emails),
            "filtered_emails": filtered_emails
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error filtering suppressed emails: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/email-automation/unsubscribe/link")
async def generate_unsubscribe_link(email: str, workflow_id: str = None, template_id: str = None):
    """
    Generate a secure unsubscribe link
    """
    try:
        unsubscribe_link = await compliance_service.generate_unsubscribe_link(
            email=email,
            workflow_id=workflow_id,
            template_id=template_id
        )
        
        return {"unsubscribe_link": unsubscribe_link}
    except Exception as e:
        logger.error(f"Error generating unsubscribe link: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/email-automation/compliance/bulk-import")
async def bulk_import_suppression_list(request: dict):
    """
    Bulk import emails to suppression list
    """
    try:
        emails = request.get("emails", [])
        reason = request.get("reason", "imported")
        
        if not emails:
            raise HTTPException(status_code=400, detail="Email list is required")
        
        result = await compliance_service.bulk_import_suppression_list(emails, reason)
        
        return {"result": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk importing suppression list: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# === BOUNCE HANDLING ===

@app.post("/api/email-automation/bounces/handle")
async def handle_email_bounce(request: dict):
    """
    Handle an email bounce
    """
    try:
        email = request.get("email")
        bounce_type = request.get("bounce_type")
        bounce_reason = request.get("bounce_reason")
        
        if not email or not bounce_type or not bounce_reason:
            raise HTTPException(status_code=400, detail="Email, bounce_type, and bounce_reason are required")
        
        resend_id = request.get("resend_id")
        template_id = request.get("template_id")
        workflow_id = request.get("workflow_id")
        details = request.get("details")
        
        success = await bounce_service.handle_bounce(
            email=email,
            bounce_type=bounce_type,
            bounce_reason=bounce_reason,
            resend_id=resend_id,
            template_id=template_id,
            workflow_id=workflow_id,
            details=details
        )
        
        if success:
            return {"message": "Bounce handled successfully", "email": email}
        else:
            raise HTTPException(status_code=400, detail="Failed to handle bounce")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling bounce: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/email-automation/bounces/delivery-failure")
async def handle_delivery_failure(request: dict):
    """
    Handle a delivery failure (for retry logic)
    """
    try:
        email = request.get("email")
        failure_reason = request.get("failure_reason")
        
        if not email or not failure_reason:
            raise HTTPException(status_code=400, detail="Email and failure_reason are required")
        
        resend_id = request.get("resend_id")
        template_id = request.get("template_id")
        workflow_id = request.get("workflow_id")
        details = request.get("details")
        
        success = await bounce_service.handle_delivery_failure(
            email=email,
            failure_reason=failure_reason,
            resend_id=resend_id,
            template_id=template_id,
            workflow_id=workflow_id,
            details=details
        )
        
        if success:
            return {"message": "Delivery failure handled successfully", "email": email}
        else:
            raise HTTPException(status_code=400, detail="Failed to handle delivery failure")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling delivery failure: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/email-automation/bounces/records")
async def get_bounce_records(limit: int = 100, offset: int = 0):
    """
    Get bounce records with pagination
    """
    try:
        records = await bounce_service.get_bounce_records(limit, offset)
        return {"bounce_records": records}
    except Exception as e:
        logger.error(f"Error getting bounce records: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/email-automation/bounces/failures")
async def get_delivery_failures(limit: int = 100, offset: int = 0):
    """
    Get delivery failure records with pagination
    """
    try:
        failures = await bounce_service.get_delivery_failures(limit, offset)
        return {"delivery_failures": failures}
    except Exception as e:
        logger.error(f"Error getting delivery failures: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/email-automation/bounces/stats")
async def get_bounce_stats():
    """
    Get bounce and delivery statistics
    """
    try:
        stats = await bounce_service.get_bounce_stats()
        return {"bounce_stats": stats}
    except Exception as e:
        logger.error(f"Error getting bounce stats: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/email-automation/bounces/retry-queue")
async def get_emails_for_retry():
    """
    Get emails that are ready for retry
    """
    try:
        retry_emails = await bounce_service.get_emails_for_retry()
        return {"retry_emails": retry_emails}
    except Exception as e:
        logger.error(f"Error getting emails for retry: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/email-automation/bounces/retry/complete")
async def mark_retry_completed(request: dict):
    """
    Mark a retry attempt as completed
    """
    try:
        email = request.get("email")
        resend_id = request.get("resend_id")
        success = request.get("success", False)
        
        if not email or not resend_id:
            raise HTTPException(status_code=400, detail="Email and resend_id are required")
        
        result = await bounce_service.mark_retry_completed(email, resend_id, success)
        
        if result:
            return {"message": "Retry completion marked successfully", "email": email, "success": success}
        else:
            raise HTTPException(status_code=400, detail="Failed to mark retry completion")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking retry completion: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/email-automation/bounces/webhook")
async def process_resend_webhook(request: dict):
    """
    Process webhook data from Resend for bounces and failures
    """
    try:
        success = await bounce_service.process_resend_webhook(request)
        
        if success:
            return {"message": "Webhook processed successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to process webhook")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/email-automation/bounces/cleanup")
async def cleanup_old_bounce_records(days_old: int = 90):
    """
    Clean up old bounce and failure records
    """
    try:
        result = await bounce_service.cleanup_old_records(days_old)
        return {"cleanup_result": result}
    except Exception as e:
        logger.error(f"Error cleaning up old records: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

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
    logger.info("🚀 AI Lead Gen API starting up...")
    logger.info("✅ Services initialized", 
                environment=os.getenv('NODE_ENV', 'development'),
                api_version=app.version)

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("👋 AI Lead Gen API shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)