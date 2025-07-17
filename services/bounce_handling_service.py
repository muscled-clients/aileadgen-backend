"""
Bounce Handling Service - Manages email bounces and delivery failures
Handles hard bounces, soft bounces, and failed deliveries to maintain sender reputation
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field
from services.email_compliance_service import EmailComplianceService
from services.email_service import EmailService
from utils.logger import logger, log_business_event

class BounceRecord(BaseModel):
    """Email bounce record model"""
    email: str
    bounce_type: str  # "hard", "soft", "complaint", "invalid"
    bounce_reason: str
    bounced_at: datetime = Field(default_factory=datetime.utcnow)
    resend_id: Optional[str] = None
    template_id: Optional[str] = None
    workflow_id: Optional[str] = None
    bounce_count: int = 1
    last_bounce_at: datetime = Field(default_factory=datetime.utcnow)
    delivery_attempts: int = 1
    details: Optional[Dict] = None

class DeliveryFailure(BaseModel):
    """Delivery failure record model"""
    email: str
    failure_reason: str
    failed_at: datetime = Field(default_factory=datetime.utcnow)
    resend_id: Optional[str] = None
    template_id: Optional[str] = None
    workflow_id: Optional[str] = None
    retry_count: int = 0
    next_retry_at: Optional[datetime] = None
    max_retries: int = 3
    details: Optional[Dict] = None

class BounceHandlingService:
    """Service for handling email bounces and delivery failures"""
    
    def __init__(self):
        self.bounce_file = "database/bounce_records.json"
        self.failure_file = "database/delivery_failures.json"
        self.compliance_service = EmailComplianceService()
        self.email_service = EmailService()
        self._ensure_files_exist()
    
    def _ensure_files_exist(self):
        """Ensure required JSON files exist"""
        for file_path in [self.bounce_file, self.failure_file]:
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    json.dump([], f)
    
    def _load_bounce_records(self) -> List[BounceRecord]:
        """Load bounce records from JSON file"""
        try:
            with open(self.bounce_file, 'r') as f:
                data = json.load(f)
                return [BounceRecord(**record) for record in data]
        except Exception as e:
            logger.error(f"Error loading bounce records: {e}")
            return []
    
    def _save_bounce_records(self, records: List[BounceRecord]):
        """Save bounce records to JSON file"""
        try:
            with open(self.bounce_file, 'w') as f:
                json.dump([record.dict() for record in records], f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving bounce records: {e}")
    
    def _load_delivery_failures(self) -> List[DeliveryFailure]:
        """Load delivery failures from JSON file"""
        try:
            with open(self.failure_file, 'r') as f:
                data = json.load(f)
                return [DeliveryFailure(**failure) for failure in data]
        except Exception as e:
            logger.error(f"Error loading delivery failures: {e}")
            return []
    
    def _save_delivery_failures(self, failures: List[DeliveryFailure]):
        """Save delivery failures to JSON file"""
        try:
            with open(self.failure_file, 'w') as f:
                json.dump([failure.dict() for failure in failures], f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving delivery failures: {e}")
    
    async def handle_bounce(self, email: str, bounce_type: str, bounce_reason: str,
                           resend_id: str = None, template_id: str = None, 
                           workflow_id: str = None, details: Dict = None) -> bool:
        """
        Handle an email bounce
        """
        try:
            email = email.lower().strip()
            
            # Load existing bounce records
            records = self._load_bounce_records()
            
            # Check if email already has bounce records
            existing_record = None
            for record in records:
                if record.email == email:
                    existing_record = record
                    break
            
            if existing_record:
                # Update existing record
                existing_record.bounce_count += 1
                existing_record.last_bounce_at = datetime.utcnow()
                existing_record.delivery_attempts += 1
                existing_record.bounce_reason = bounce_reason
                existing_record.bounce_type = bounce_type
                if details:
                    existing_record.details = details
            else:
                # Create new bounce record
                new_record = BounceRecord(
                    email=email,
                    bounce_type=bounce_type,
                    bounce_reason=bounce_reason,
                    resend_id=resend_id,
                    template_id=template_id,
                    workflow_id=workflow_id,
                    details=details
                )
                records.append(new_record)
            
            # Save updated records
            self._save_bounce_records(records)
            
            # Handle based on bounce type
            if bounce_type == "hard":
                # Hard bounce - add to suppression list immediately
                await self.compliance_service.add_to_suppression_list(
                    email=email,
                    reason="bounced",
                    source="bounce_handler",
                    details={"bounce_reason": bounce_reason, "bounce_type": bounce_type}
                )
                logger.info(f"Hard bounce handled - email suppressed: {email}")
                
            elif bounce_type == "soft":
                # Soft bounce - check if we should suppress after multiple attempts
                current_record = existing_record or records[-1]
                if current_record.bounce_count >= 5:  # Suppress after 5 soft bounces
                    await self.compliance_service.add_to_suppression_list(
                        email=email,
                        reason="bounced",
                        source="bounce_handler",
                        details={"bounce_reason": bounce_reason, "bounce_type": bounce_type}
                    )
                    logger.info(f"Soft bounce limit reached - email suppressed: {email}")
                    
            elif bounce_type == "complaint":
                # Complaint/spam - add to suppression list immediately
                await self.compliance_service.add_to_suppression_list(
                    email=email,
                    reason="complained",
                    source="bounce_handler",
                    details={"bounce_reason": bounce_reason, "bounce_type": bounce_type}
                )
                logger.info(f"Complaint handled - email suppressed: {email}")
            
            # Update email history status
            await self.email_service.update_email_status(
                email_id=resend_id,
                status="bounced",
                error_message=bounce_reason
            )
            
            log_business_event(
                event="email_bounced",
                entity_type="email",
                entity_id=email,
                details={
                    "bounce_type": bounce_type,
                    "bounce_reason": bounce_reason,
                    "resend_id": resend_id,
                    "template_id": template_id,
                    "workflow_id": workflow_id
                }
            )
            
            logger.info(f"Bounce handled successfully: {email} - {bounce_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling bounce: {e}")
            return False
    
    async def handle_delivery_failure(self, email: str, failure_reason: str,
                                     resend_id: str = None, template_id: str = None,
                                     workflow_id: str = None, details: Dict = None) -> bool:
        """
        Handle a delivery failure (for retry logic)
        """
        try:
            email = email.lower().strip()
            
            # Load existing failures
            failures = self._load_delivery_failures()
            
            # Check if email already has a failure record
            existing_failure = None
            for failure in failures:
                if failure.email == email and failure.resend_id == resend_id:
                    existing_failure = failure
                    break
            
            if existing_failure:
                # Update existing failure
                existing_failure.retry_count += 1
                existing_failure.failed_at = datetime.utcnow()
                existing_failure.failure_reason = failure_reason
                if details:
                    existing_failure.details = details
                
                # Check if we should retry
                if existing_failure.retry_count < existing_failure.max_retries:
                    # Schedule retry (exponential backoff)
                    retry_delay = 2 ** existing_failure.retry_count * 60  # Minutes
                    existing_failure.next_retry_at = datetime.utcnow() + timedelta(minutes=retry_delay)
                    logger.info(f"Delivery failure - scheduled retry {existing_failure.retry_count}/{existing_failure.max_retries} for {email}")
                else:
                    # Max retries reached - treat as bounce
                    await self.handle_bounce(
                        email=email,
                        bounce_type="hard",
                        bounce_reason=f"Max retry attempts reached: {failure_reason}",
                        resend_id=resend_id,
                        template_id=template_id,
                        workflow_id=workflow_id,
                        details=details
                    )
                    logger.info(f"Max retries reached - treating as hard bounce: {email}")
            else:
                # Create new failure record
                new_failure = DeliveryFailure(
                    email=email,
                    failure_reason=failure_reason,
                    resend_id=resend_id,
                    template_id=template_id,
                    workflow_id=workflow_id,
                    details=details,
                    next_retry_at=datetime.utcnow() + timedelta(minutes=5)  # First retry in 5 minutes
                )
                failures.append(new_failure)
                logger.info(f"New delivery failure recorded for {email}")
            
            # Save updated failures
            self._save_delivery_failures(failures)
            
            # Update email history status
            await self.email_service.update_email_status(
                email_id=resend_id,
                status="failed",
                error_message=failure_reason
            )
            
            log_business_event(
                event="email_delivery_failed",
                entity_type="email",
                entity_id=email,
                details={
                    "failure_reason": failure_reason,
                    "resend_id": resend_id,
                    "retry_count": existing_failure.retry_count if existing_failure else 0
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling delivery failure: {e}")
            return False
    
    async def get_bounce_records(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Get bounce records with pagination
        """
        try:
            records = self._load_bounce_records()
            
            # Sort by last_bounce_at desc
            records.sort(key=lambda x: x.last_bounce_at, reverse=True)
            
            # Apply pagination
            paginated = records[offset:offset + limit]
            
            return [record.dict() for record in paginated]
            
        except Exception as e:
            logger.error(f"Error getting bounce records: {e}")
            return []
    
    async def get_delivery_failures(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Get delivery failure records with pagination
        """
        try:
            failures = self._load_delivery_failures()
            
            # Sort by failed_at desc
            failures.sort(key=lambda x: x.failed_at, reverse=True)
            
            # Apply pagination
            paginated = failures[offset:offset + limit]
            
            return [failure.dict() for failure in paginated]
            
        except Exception as e:
            logger.error(f"Error getting delivery failures: {e}")
            return []
    
    async def get_bounce_stats(self) -> Dict:
        """
        Get bounce and delivery statistics
        """
        try:
            records = self._load_bounce_records()
            failures = self._load_delivery_failures()
            
            # Calculate bounce stats
            total_bounces = len(records)
            hard_bounces = len([r for r in records if r.bounce_type == "hard"])
            soft_bounces = len([r for r in records if r.bounce_type == "soft"])
            complaints = len([r for r in records if r.bounce_type == "complaint"])
            
            # Recent bounces (last 24 hours)
            recent_bounces = [
                r for r in records 
                if (datetime.utcnow() - r.last_bounce_at).total_seconds() < 86400
            ]
            
            # Delivery failure stats
            total_failures = len(failures)
            pending_retries = len([f for f in failures if f.next_retry_at and f.next_retry_at > datetime.utcnow()])
            failed_retries = len([f for f in failures if f.retry_count >= f.max_retries])
            
            return {
                "total_bounces": total_bounces,
                "hard_bounces": hard_bounces,
                "soft_bounces": soft_bounces,
                "complaints": complaints,
                "recent_bounces": len(recent_bounces),
                "total_failures": total_failures,
                "pending_retries": pending_retries,
                "failed_retries": failed_retries,
                "bounce_rate": self._calculate_bounce_rate(),
                "top_bounce_reasons": self._get_top_bounce_reasons(records)
            }
            
        except Exception as e:
            logger.error(f"Error getting bounce stats: {e}")
            return {}
    
    def _calculate_bounce_rate(self) -> float:
        """
        Calculate the bounce rate based on recent activity
        """
        try:
            # This would ideally calculate based on emails sent vs bounces
            # For now, return a placeholder
            return 0.03  # 3% bounce rate
            
        except Exception as e:
            logger.error(f"Error calculating bounce rate: {e}")
            return 0.0
    
    def _get_top_bounce_reasons(self, records: List[BounceRecord]) -> List[Dict]:
        """
        Get the top bounce reasons
        """
        try:
            reason_counts = {}
            for record in records:
                reason = record.bounce_reason
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            
            # Sort by count and return top 10
            sorted_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)
            
            return [
                {"reason": reason, "count": count}
                for reason, count in sorted_reasons[:10]
            ]
            
        except Exception as e:
            logger.error(f"Error getting top bounce reasons: {e}")
            return []
    
    async def get_emails_for_retry(self) -> List[Dict]:
        """
        Get emails that are ready for retry
        """
        try:
            failures = self._load_delivery_failures()
            now = datetime.utcnow()
            
            retry_emails = []
            for failure in failures:
                if (failure.next_retry_at and failure.next_retry_at <= now and 
                    failure.retry_count < failure.max_retries):
                    retry_emails.append(failure.dict())
            
            return retry_emails
            
        except Exception as e:
            logger.error(f"Error getting emails for retry: {e}")
            return []
    
    async def mark_retry_completed(self, email: str, resend_id: str, success: bool) -> bool:
        """
        Mark a retry attempt as completed
        """
        try:
            failures = self._load_delivery_failures()
            
            for failure in failures:
                if failure.email == email and failure.resend_id == resend_id:
                    if success:
                        # Remove from failures list
                        failures.remove(failure)
                        logger.info(f"Retry successful - removed from failures: {email}")
                    else:
                        # Increment retry count
                        failure.retry_count += 1
                        failure.failed_at = datetime.utcnow()
                        
                        if failure.retry_count >= failure.max_retries:
                            # Max retries reached
                            await self.handle_bounce(
                                email=email,
                                bounce_type="hard",
                                bounce_reason="Max retry attempts reached",
                                resend_id=resend_id
                            )
                        else:
                            # Schedule next retry
                            retry_delay = 2 ** failure.retry_count * 60
                            failure.next_retry_at = datetime.utcnow() + timedelta(minutes=retry_delay)
                    
                    break
            
            self._save_delivery_failures(failures)
            return True
            
        except Exception as e:
            logger.error(f"Error marking retry completed: {e}")
            return False
    
    async def process_resend_webhook(self, webhook_data: Dict) -> bool:
        """
        Process webhook data from Resend for bounces and failures
        """
        try:
            event_type = webhook_data.get("type")
            data = webhook_data.get("data", {})
            
            email = data.get("to", [{}])[0].get("email") if data.get("to") else None
            if not email:
                logger.warning("No email found in webhook data")
                return False
            
            resend_id = data.get("id")
            
            if event_type == "email.bounced":
                bounce_type = "hard"  # Default to hard bounce
                bounce_reason = data.get("reason", "Unknown bounce reason")
                
                # Determine bounce type from reason
                if "soft" in bounce_reason.lower() or "temporary" in bounce_reason.lower():
                    bounce_type = "soft"
                elif "complaint" in bounce_reason.lower() or "spam" in bounce_reason.lower():
                    bounce_type = "complaint"
                
                await self.handle_bounce(
                    email=email,
                    bounce_type=bounce_type,
                    bounce_reason=bounce_reason,
                    resend_id=resend_id,
                    details=webhook_data
                )
                
            elif event_type == "email.delivery_delayed":
                failure_reason = data.get("reason", "Delivery delayed")
                await self.handle_delivery_failure(
                    email=email,
                    failure_reason=failure_reason,
                    resend_id=resend_id,
                    details=webhook_data
                )
                
            elif event_type == "email.complained":
                await self.handle_bounce(
                    email=email,
                    bounce_type="complaint",
                    bounce_reason="Spam complaint",
                    resend_id=resend_id,
                    details=webhook_data
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing Resend webhook: {e}")
            return False
    
    async def cleanup_old_records(self, days_old: int = 90) -> Dict:
        """
        Clean up old bounce and failure records
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Clean bounce records
            records = self._load_bounce_records()
            original_bounce_count = len(records)
            records = [r for r in records if r.last_bounce_at > cutoff_date]
            self._save_bounce_records(records)
            
            # Clean failure records
            failures = self._load_delivery_failures()
            original_failure_count = len(failures)
            failures = [f for f in failures if f.failed_at > cutoff_date]
            self._save_delivery_failures(failures)
            
            cleaned_bounces = original_bounce_count - len(records)
            cleaned_failures = original_failure_count - len(failures)
            
            logger.info(f"Cleaned up {cleaned_bounces} bounce records and {cleaned_failures} failure records")
            
            return {
                "cleaned_bounces": cleaned_bounces,
                "cleaned_failures": cleaned_failures,
                "remaining_bounces": len(records),
                "remaining_failures": len(failures)
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up old records: {e}")
            return {"error": str(e)}