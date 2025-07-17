"""
Email Service - Resend Integration
Handles all email sending functionality for automation workflows
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import resend
from utils.logger import logger, log_business_event

# Initialize Resend client
resend.api_key = os.getenv("RESEND_API_KEY")

class EmailTemplate(BaseModel):
    """Email template model"""
    id: str
    name: str
    subject: str
    content: str
    variables: List[str] = []
    workflow_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class EmailSendRequest(BaseModel):
    """Email send request model"""
    to_email: str
    to_name: str
    subject: str
    content: str
    template_id: Optional[str] = None
    workflow_id: Optional[str] = None
    lead_id: Optional[str] = None
    variables: Dict[str, str] = {}

class EmailSendResult(BaseModel):
    """Email send result model"""
    success: bool
    email_id: Optional[str] = None
    error_message: Optional[str] = None
    resend_id: Optional[str] = None

class EmailService:
    """Service for handling email operations"""
    
    def __init__(self):
        self.templates_file = "database/email_templates.json"
        self.email_history_file = "database/email_history.json"
        self._ensure_files_exist()
    
    def _ensure_files_exist(self):
        """Ensure required JSON files exist"""
        for file_path in [self.templates_file, self.email_history_file]:
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    json.dump([], f)
    
    def _load_templates(self) -> List[EmailTemplate]:
        """Load email templates from JSON file"""
        try:
            with open(self.templates_file, 'r') as f:
                data = json.load(f)
                return [EmailTemplate(**template) for template in data]
        except Exception as e:
            logger.error(f"Error loading templates: {e}")
            return []
    
    def _save_templates(self, templates: List[EmailTemplate]):
        """Save email templates to JSON file"""
        try:
            with open(self.templates_file, 'w') as f:
                json.dump([template.dict() for template in templates], f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving templates: {e}")
    
    def _load_email_history(self) -> List[Dict]:
        """Load email history from JSON file"""
        try:
            with open(self.email_history_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading email history: {e}")
            return []
    
    def _save_email_history(self, history: List[Dict]):
        """Save email history to JSON file"""
        try:
            with open(self.email_history_file, 'w') as f:
                json.dump(history, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving email history: {e}")
    
    def _replace_variables(self, content: str, variables: Dict[str, str]) -> str:
        """Replace template variables with actual values"""
        for key, value in variables.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))
        return content
    
    async def create_template(self, template_data: Dict) -> EmailTemplate:
        """Create a new email template"""
        try:
            # Generate template ID
            template_id = f"template_{len(self._load_templates()) + 1}_{int(datetime.utcnow().timestamp())}"
            
            template = EmailTemplate(
                id=template_id,
                name=template_data.get("name", ""),
                subject=template_data.get("subject", ""),
                content=template_data.get("content", ""),
                variables=template_data.get("variables", []),
                workflow_id=template_data.get("workflow_id")
            )
            
            # Save to database
            templates = self._load_templates()
            templates.append(template)
            self._save_templates(templates)
            
            log_business_event(
                event="email_template_created",
                entity_type="email_template",
                entity_id=template.id,
                details={"name": template.name, "workflow_id": template.workflow_id}
            )
            
            logger.info(f"Created email template: {template.id}")
            return template
            
        except Exception as e:
            logger.error(f"Error creating email template: {e}")
            raise
    
    async def get_template(self, template_id: str) -> Optional[EmailTemplate]:
        """Get email template by ID"""
        templates = self._load_templates()
        for template in templates:
            if template.id == template_id:
                return template
        return None
    
    async def get_templates_by_workflow(self, workflow_id: str) -> List[EmailTemplate]:
        """Get all templates for a specific workflow"""
        templates = self._load_templates()
        return [t for t in templates if t.workflow_id == workflow_id]
    
    async def update_template(self, template_id: str, template_data: Dict) -> Optional[EmailTemplate]:
        """Update an existing email template"""
        try:
            templates = self._load_templates()
            
            for i, template in enumerate(templates):
                if template.id == template_id:
                    # Update template
                    template.name = template_data.get("name", template.name)
                    template.subject = template_data.get("subject", template.subject)
                    template.content = template_data.get("content", template.content)
                    template.variables = template_data.get("variables", template.variables)
                    template.updated_at = datetime.utcnow()
                    
                    templates[i] = template
                    self._save_templates(templates)
                    
                    logger.info(f"Updated email template: {template_id}")
                    return template
            
            return None
            
        except Exception as e:
            logger.error(f"Error updating email template: {e}")
            raise
    
    async def delete_template(self, template_id: str) -> bool:
        """Delete an email template"""
        try:
            templates = self._load_templates()
            original_count = len(templates)
            
            templates = [t for t in templates if t.id != template_id]
            
            if len(templates) < original_count:
                self._save_templates(templates)
                logger.info(f"Deleted email template: {template_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting email template: {e}")
            return False
    
    async def send_email(self, email_request: EmailSendRequest) -> EmailSendResult:
        """Send an email using Resend"""
        try:
            # Replace variables in subject and content
            subject = self._replace_variables(email_request.subject, email_request.variables)
            content = self._replace_variables(email_request.content, email_request.variables)
            
            # Prepare email data
            email_data = {
                "from": "AI Lead Gen <noreply@aileadgen.dev>",
                "to": [f"{email_request.to_name} <{email_request.to_email}>"],
                "subject": subject,
                "html": content.replace('\n', '<br>'),
                "text": content
            }
            
            # Send email via Resend
            response = resend.Emails.send(email_data)
            
            # Log email history
            email_history = self._load_email_history()
            email_record = {
                "id": response.get("id", f"email_{int(datetime.utcnow().timestamp())}"),
                "to_email": email_request.to_email,
                "to_name": email_request.to_name,
                "subject": subject,
                "content": content,
                "template_id": email_request.template_id,
                "workflow_id": email_request.workflow_id,
                "lead_id": email_request.lead_id,
                "resend_id": response.get("id"),
                "status": "sent",
                "sent_at": datetime.utcnow().isoformat(),
                "opened_at": None,
                "clicked_at": None,
                "failed_at": None,
                "error_message": None
            }
            
            email_history.append(email_record)
            self._save_email_history(email_history)
            
            log_business_event(
                event="email_sent",
                entity_type="email",
                entity_id=email_record["id"],
                details={
                    "to_email": email_request.to_email,
                    "subject": subject,
                    "workflow_id": email_request.workflow_id,
                    "template_id": email_request.template_id
                }
            )
            
            logger.info(f"Email sent successfully to {email_request.to_email}")
            
            return EmailSendResult(
                success=True,
                email_id=email_record["id"],
                resend_id=response.get("id")
            )
            
        except Exception as e:
            logger.error(f"Error sending email to {email_request.to_email}: {e}")
            
            # Log failed email
            email_history = self._load_email_history()
            email_record = {
                "id": f"email_{int(datetime.utcnow().timestamp())}",
                "to_email": email_request.to_email,
                "to_name": email_request.to_name,
                "subject": email_request.subject,
                "content": email_request.content,
                "template_id": email_request.template_id,
                "workflow_id": email_request.workflow_id,
                "lead_id": email_request.lead_id,
                "resend_id": None,
                "status": "failed",
                "sent_at": datetime.utcnow().isoformat(),
                "opened_at": None,
                "clicked_at": None,
                "failed_at": datetime.utcnow().isoformat(),
                "error_message": str(e)
            }
            
            email_history.append(email_record)
            self._save_email_history(email_history)
            
            return EmailSendResult(
                success=False,
                error_message=str(e)
            )
    
    async def get_email_history(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get email history with pagination"""
        history = self._load_email_history()
        
        # Sort by sent_at desc
        history.sort(key=lambda x: x.get("sent_at", ""), reverse=True)
        
        return history[offset:offset + limit]
    
    async def get_email_history_by_workflow(self, workflow_id: str) -> List[Dict]:
        """Get email history for a specific workflow"""
        history = self._load_email_history()
        return [email for email in history if email.get("workflow_id") == workflow_id]
    
    async def get_email_history_by_lead(self, lead_id: str) -> List[Dict]:
        """Get email history for a specific lead"""
        history = self._load_email_history()
        return [email for email in history if email.get("lead_id") == lead_id]
    
    async def update_email_status(self, email_id: str, status: str, **kwargs):
        """Update email status (for webhook processing)"""
        try:
            history = self._load_email_history()
            
            for i, email in enumerate(history):
                if email.get("id") == email_id or email.get("resend_id") == email_id:
                    email["status"] = status
                    
                    if status == "delivered":
                        email["delivered_at"] = datetime.utcnow().isoformat()
                    elif status == "opened":
                        email["opened_at"] = datetime.utcnow().isoformat()
                    elif status == "clicked":
                        email["clicked_at"] = datetime.utcnow().isoformat()
                    elif status == "bounced":
                        email["bounced_at"] = datetime.utcnow().isoformat()
                    elif status == "failed":
                        email["failed_at"] = datetime.utcnow().isoformat()
                        email["error_message"] = kwargs.get("error_message", "")
                    
                    history[i] = email
                    break
            
            self._save_email_history(history)
            logger.info(f"Updated email status: {email_id} -> {status}")
            
        except Exception as e:
            logger.error(f"Error updating email status: {e}")
    
    async def send_test_email(self, to_email: str, template_id: str, variables: Dict[str, str] = None) -> EmailSendResult:
        """Send a test email"""
        try:
            template = await self.get_template(template_id)
            if not template:
                return EmailSendResult(success=False, error_message="Template not found")
            
            # Use default test variables if none provided
            if not variables:
                variables = {
                    "name": "Test User",
                    "email": to_email,
                    "niche": "real estate",
                    "company_name": "Test Company",
                    "revenue": "$40K - $80K",
                    "pain_point": "Need more leads",
                    "calendar_link": "https://calendly.com/test",
                    "profile_link": "https://app.aileadgen.dev/profile"
                }
            
            request = EmailSendRequest(
                to_email=to_email,
                to_name=variables.get("name", "Test User"),
                subject=f"[TEST] {template.subject}",
                content=template.content,
                template_id=template.id,
                variables=variables
            )
            
            return await self.send_email(request)
            
        except Exception as e:
            logger.error(f"Error sending test email: {e}")
            return EmailSendResult(success=False, error_message=str(e))