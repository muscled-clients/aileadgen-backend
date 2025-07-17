"""
Email Lead Service - Connects email automation with existing lead database
Handles lead-based email automation triggers and workflows
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from services.email_service import EmailService, EmailSendRequest
from services.simple_lead_service import SimpleLeadService
from utils.logger import logger, log_business_event

class EmailLeadService:
    """Service to connect email automation with lead management"""
    
    def __init__(self):
        self.email_service = EmailService()
        self.lead_service = SimpleLeadService()
    
    async def send_welcome_email(self, lead_id: str) -> bool:
        """
        Send welcome email to a new lead
        """
        try:
            # Get lead data
            lead = await self.lead_service.get_lead_by_id(lead_id)
            if not lead:
                logger.error(f"Lead not found: {lead_id}")
                return False
            
            # Get welcome template (we'll create a default one)
            welcome_template = await self._get_or_create_welcome_template()
            
            # Prepare email variables
            variables = {
                "name": lead.name,
                "email": lead.email,
                "niche": lead.niche,
                "company_name": lead.name + " Company",  # Default company name
                "revenue": lead.monthly_revenue,
                "pain_point": lead.pain_point,
                "calendar_link": "https://calendly.com/aileadgen/demo",
                "profile_link": "https://app.aileadgen.dev/profile"
            }
            
            # Send email
            email_request = EmailSendRequest(
                to_email=lead.email,
                to_name=lead.name,
                subject=welcome_template.subject,
                content=welcome_template.content,
                template_id=welcome_template.id,
                lead_id=lead_id,
                variables=variables
            )
            
            result = await self.email_service.send_email(email_request)
            
            if result.success:
                log_business_event(
                    event="welcome_email_sent",
                    entity_type="lead",
                    entity_id=lead_id,
                    details={"email": lead.email, "template_id": welcome_template.id}
                )
                logger.info(f"Welcome email sent to lead: {lead_id}")
                return True
            else:
                logger.error(f"Failed to send welcome email: {result.error_message}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending welcome email: {e}")
            return False
    
    async def send_qualification_email(self, lead_id: str) -> bool:
        """
        Send qualification email to a qualified lead
        """
        try:
            # Get lead data
            lead = await self.lead_service.get_lead_by_id(lead_id)
            if not lead or not lead.qualified:
                logger.error(f"Lead not found or not qualified: {lead_id}")
                return False
            
            # Get qualification template
            qualification_template = await self._get_or_create_qualification_template()
            
            # Prepare email variables
            variables = {
                "name": lead.name,
                "email": lead.email,
                "niche": lead.niche,
                "revenue": lead.monthly_revenue,
                "pain_point": lead.pain_point,
                "calendar_link": "https://calendly.com/aileadgen/qualified-demo",
                "profile_link": "https://app.aileadgen.dev/profile"
            }
            
            # Send email
            email_request = EmailSendRequest(
                to_email=lead.email,
                to_name=lead.name,
                subject=qualification_template.subject,
                content=qualification_template.content,
                template_id=qualification_template.id,
                lead_id=lead_id,
                variables=variables
            )
            
            result = await self.email_service.send_email(email_request)
            
            if result.success:
                log_business_event(
                    event="qualification_email_sent",
                    entity_type="lead",
                    entity_id=lead_id,
                    details={"email": lead.email, "template_id": qualification_template.id}
                )
                logger.info(f"Qualification email sent to lead: {lead_id}")
                return True
            else:
                logger.error(f"Failed to send qualification email: {result.error_message}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending qualification email: {e}")
            return False
    
    async def send_follow_up_email(self, lead_id: str, follow_up_type: str = "general") -> bool:
        """
        Send follow-up email to a lead
        """
        try:
            # Get lead data
            lead = await self.lead_service.get_lead_by_id(lead_id)
            if not lead:
                logger.error(f"Lead not found: {lead_id}")
                return False
            
            # Get follow-up template
            follow_up_template = await self._get_or_create_follow_up_template(follow_up_type)
            
            # Prepare email variables
            variables = {
                "name": lead.name,
                "email": lead.email,
                "niche": lead.niche,
                "revenue": lead.monthly_revenue,
                "pain_point": lead.pain_point,
                "calendar_link": "https://calendly.com/aileadgen/follow-up",
                "profile_link": "https://app.aileadgen.dev/profile"
            }
            
            # Send email
            email_request = EmailSendRequest(
                to_email=lead.email,
                to_name=lead.name,
                subject=follow_up_template.subject,
                content=follow_up_template.content,
                template_id=follow_up_template.id,
                lead_id=lead_id,
                variables=variables
            )
            
            result = await self.email_service.send_email(email_request)
            
            if result.success:
                log_business_event(
                    event="follow_up_email_sent",
                    entity_type="lead",
                    entity_id=lead_id,
                    details={"email": lead.email, "template_id": follow_up_template.id, "type": follow_up_type}
                )
                logger.info(f"Follow-up email sent to lead: {lead_id}")
                return True
            else:
                logger.error(f"Failed to send follow-up email: {result.error_message}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending follow-up email: {e}")
            return False
    
    async def get_lead_email_history(self, lead_id: str) -> List[Dict]:
        """
        Get email history for a specific lead
        """
        try:
            history = await self.email_service.get_email_history_by_lead(lead_id)
            return history
        except Exception as e:
            logger.error(f"Error getting lead email history: {e}")
            return []
    
    async def trigger_lead_workflow(self, lead_id: str, trigger_type: str) -> bool:
        """
        Trigger email workflow based on lead actions
        """
        try:
            logger.info(f"Triggering workflow for lead {lead_id}: {trigger_type}")
            
            if trigger_type == "new_lead":
                return await self.send_welcome_email(lead_id)
            elif trigger_type == "qualified":
                return await self.send_qualification_email(lead_id)
            elif trigger_type == "follow_up":
                return await self.send_follow_up_email(lead_id)
            else:
                logger.warning(f"Unknown trigger type: {trigger_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error triggering lead workflow: {e}")
            return False
    
    async def process_lead_for_automation(self, lead_id: str) -> Dict:
        """
        Process a lead for email automation based on their current status
        """
        try:
            lead = await self.lead_service.get_lead_by_id(lead_id)
            if not lead:
                return {"error": "Lead not found"}
            
            result = {"lead_id": lead_id, "actions": []}
            
            # Get existing email history
            email_history = await self.get_lead_email_history(lead_id)
            sent_types = [email.get("template_id", "") for email in email_history]
            
            # Determine what emails to send
            if lead.completion_status == "complete":
                # Welcome email if not sent
                if not any("welcome" in template_id for template_id in sent_types):
                    success = await self.send_welcome_email(lead_id)
                    result["actions"].append({"type": "welcome", "success": success})
                
                # Qualification email if qualified and not sent
                if lead.qualified and not any("qualification" in template_id for template_id in sent_types):
                    success = await self.send_qualification_email(lead_id)
                    result["actions"].append({"type": "qualification", "success": success})
            
            # Follow-up email if no recent activity
            if email_history:
                last_email = max(email_history, key=lambda x: x.get("sent_at", ""))
                last_sent = datetime.fromisoformat(last_email.get("sent_at", ""))
                days_since_last = (datetime.utcnow() - last_sent).days
                
                if days_since_last >= 3:  # Send follow-up after 3 days
                    success = await self.send_follow_up_email(lead_id)
                    result["actions"].append({"type": "follow_up", "success": success})
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing lead for automation: {e}")
            return {"error": str(e)}
    
    async def bulk_process_leads(self, lead_ids: List[str]) -> Dict:
        """
        Process multiple leads for email automation
        """
        try:
            results = []
            
            for lead_id in lead_ids:
                result = await self.process_lead_for_automation(lead_id)
                results.append(result)
            
            return {"results": results, "processed_count": len(results)}
            
        except Exception as e:
            logger.error(f"Error bulk processing leads: {e}")
            return {"error": str(e)}
    
    # Helper methods to get or create default templates
    async def _get_or_create_welcome_template(self):
        """Get or create default welcome template"""
        try:
            templates = self.email_service._load_templates()
            welcome_template = next((t for t in templates if "welcome" in t.name.lower()), None)
            
            if not welcome_template:
                template_data = {
                    "name": "Welcome Email Template",
                    "subject": "Welcome to AI Lead Gen, {{name}}!",
                    "content": """Hi {{name}},

Welcome to AI Lead Gen! We're excited to help you scale your {{niche}} business.

Based on your profile, we understand you're currently generating {{revenue}} monthly and looking to solve: {{pain_point}}.

Here's what we can help you with:
• Generate 100+ qualified leads per month
• Automated AI calling system
• Complete lead management dashboard
• Real-time analytics and reporting

Ready to get started? Book your demo call here: {{calendar_link}}

Best regards,
AI Lead Gen Team

---
Manage your preferences: {{profile_link}}
""",
                    "variables": ["name", "niche", "revenue", "pain_point", "calendar_link", "profile_link"]
                }
                welcome_template = await self.email_service.create_template(template_data)
            
            return welcome_template
            
        except Exception as e:
            logger.error(f"Error getting welcome template: {e}")
            raise
    
    async def _get_or_create_qualification_template(self):
        """Get or create default qualification template"""
        try:
            templates = self.email_service._load_templates()
            qualification_template = next((t for t in templates if "qualification" in t.name.lower()), None)
            
            if not qualification_template:
                template_data = {
                    "name": "Qualification Email Template",
                    "subject": "Perfect! You're qualified for our {{niche}} program",
                    "content": """Hi {{name}},

Great news! Based on your responses, you're a perfect fit for our AI Lead Gen program.

Here's what makes you qualified:
• Monthly Revenue: {{revenue}} ✓
• Pain Point: {{pain_point}} ✓
• Industry: {{niche}} ✓

Next steps:
1. Book your priority demo call: {{calendar_link}}
2. We'll show you exactly how to 3x your leads
3. Get started within 24 hours

This priority booking is only available for qualified leads like yourself.

Book now: {{calendar_link}}

Best regards,
AI Lead Gen Team

---
Manage your preferences: {{profile_link}}
""",
                    "variables": ["name", "niche", "revenue", "pain_point", "calendar_link", "profile_link"]
                }
                qualification_template = await self.email_service.create_template(template_data)
            
            return qualification_template
            
        except Exception as e:
            logger.error(f"Error getting qualification template: {e}")
            raise
    
    async def _get_or_create_follow_up_template(self, follow_up_type: str = "general"):
        """Get or create default follow-up template"""
        try:
            templates = self.email_service._load_templates()
            follow_up_template = next((t for t in templates if "follow" in t.name.lower()), None)
            
            if not follow_up_template:
                template_data = {
                    "name": "Follow-up Email Template",
                    "subject": "Don't miss out on 3x more {{niche}} leads, {{name}}",
                    "content": """Hi {{name}},

I wanted to follow up on our AI Lead Gen solution for your {{niche}} business.

You mentioned struggling with: {{pain_point}}

Here's what other {{niche}} businesses are saying:
• "Increased leads by 300% in 30 days"
• "AI calling system saved us 20 hours/week"
• "Best ROI we've ever seen"

With your {{revenue}} monthly revenue, you're missing out on significant growth opportunities.

Ready to see how it works?
Book your demo: {{calendar_link}}

Best regards,
AI Lead Gen Team

P.S. We have limited spots available this month. Don't wait!

---
Manage your preferences: {{profile_link}}
""",
                    "variables": ["name", "niche", "revenue", "pain_point", "calendar_link", "profile_link"]
                }
                follow_up_template = await self.email_service.create_template(template_data)
            
            return follow_up_template
            
        except Exception as e:
            logger.error(f"Error getting follow-up template: {e}")
            raise