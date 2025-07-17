"""
Email Compliance Service - Handles email marketing compliance
Manages unsubscribe links, suppression lists, and legal compliance
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field
from utils.logger import logger, log_business_event

class UnsubscribeRecord(BaseModel):
    """Unsubscribe record model"""
    email: str
    unsubscribed_at: datetime = Field(default_factory=datetime.utcnow)
    reason: Optional[str] = None
    source: str = "email_link"  # "email_link", "manual", "bounce"
    workflow_id: Optional[str] = None
    template_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class SuppressionList(BaseModel):
    """Suppression list model for managing blocked emails"""
    email: str
    reason: str  # "unsubscribed", "bounced", "complained", "invalid"
    added_at: datetime = Field(default_factory=datetime.utcnow)
    source: str
    details: Optional[Dict] = None

class EmailComplianceService:
    """Service for managing email compliance and suppression"""
    
    def __init__(self):
        self.unsubscribe_file = "database/unsubscribe_records.json"
        self.suppression_file = "database/suppression_list.json"
        self._ensure_files_exist()
    
    def _ensure_files_exist(self):
        """Ensure required JSON files exist"""
        for file_path in [self.unsubscribe_file, self.suppression_file]:
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    json.dump([], f)
    
    def _load_unsubscribe_records(self) -> List[UnsubscribeRecord]:
        """Load unsubscribe records from JSON file"""
        try:
            with open(self.unsubscribe_file, 'r') as f:
                data = json.load(f)
                return [UnsubscribeRecord(**record) for record in data]
        except Exception as e:
            logger.error(f"Error loading unsubscribe records: {e}")
            return []
    
    def _save_unsubscribe_records(self, records: List[UnsubscribeRecord]):
        """Save unsubscribe records to JSON file"""
        try:
            with open(self.unsubscribe_file, 'w') as f:
                json.dump([record.dict() for record in records], f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving unsubscribe records: {e}")
    
    def _load_suppression_list(self) -> List[SuppressionList]:
        """Load suppression list from JSON file"""
        try:
            with open(self.suppression_file, 'r') as f:
                data = json.load(f)
                return [SuppressionList(**item) for item in data]
        except Exception as e:
            logger.error(f"Error loading suppression list: {e}")
            return []
    
    def _save_suppression_list(self, suppressions: List[SuppressionList]):
        """Save suppression list to JSON file"""
        try:
            with open(self.suppression_file, 'w') as f:
                json.dump([item.dict() for item in suppressions], f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving suppression list: {e}")
    
    async def unsubscribe_email(self, email: str, reason: str = None, source: str = "email_link", 
                               workflow_id: str = None, template_id: str = None, 
                               ip_address: str = None, user_agent: str = None) -> bool:
        """
        Unsubscribe an email address from all email communications
        """
        try:
            email = email.lower().strip()
            
            # Check if already unsubscribed
            if await self.is_email_suppressed(email):
                logger.info(f"Email already unsubscribed: {email}")
                return True
            
            # Create unsubscribe record
            unsubscribe_record = UnsubscribeRecord(
                email=email,
                reason=reason,
                source=source,
                workflow_id=workflow_id,
                template_id=template_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Save unsubscribe record
            records = self._load_unsubscribe_records()
            records.append(unsubscribe_record)
            self._save_unsubscribe_records(records)
            
            # Add to suppression list
            suppression_item = SuppressionList(
                email=email,
                reason="unsubscribed",
                source=source,
                details={
                    "workflow_id": workflow_id,
                    "template_id": template_id,
                    "user_reason": reason
                }
            )
            
            suppressions = self._load_suppression_list()
            suppressions.append(suppression_item)
            self._save_suppression_list(suppressions)
            
            log_business_event(
                event="email_unsubscribed",
                entity_type="email",
                entity_id=email,
                details={
                    "reason": reason,
                    "source": source,
                    "workflow_id": workflow_id,
                    "template_id": template_id
                }
            )
            
            logger.info(f"Email unsubscribed successfully: {email}")
            return True
            
        except Exception as e:
            logger.error(f"Error unsubscribing email: {e}")
            return False
    
    async def is_email_suppressed(self, email: str) -> bool:
        """
        Check if an email is on the suppression list
        """
        try:
            email = email.lower().strip()
            suppressions = self._load_suppression_list()
            
            for suppression in suppressions:
                if suppression.email == email:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking email suppression: {e}")
            return False
    
    async def get_suppression_reason(self, email: str) -> Optional[str]:
        """
        Get the reason why an email is suppressed
        """
        try:
            email = email.lower().strip()
            suppressions = self._load_suppression_list()
            
            for suppression in suppressions:
                if suppression.email == email:
                    return suppression.reason
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting suppression reason: {e}")
            return None
    
    async def remove_from_suppression_list(self, email: str) -> bool:
        """
        Remove an email from the suppression list (resubscribe)
        """
        try:
            email = email.lower().strip()
            suppressions = self._load_suppression_list()
            original_count = len(suppressions)
            
            # Remove from suppression list
            suppressions = [s for s in suppressions if s.email != email]
            
            if len(suppressions) < original_count:
                self._save_suppression_list(suppressions)
                
                log_business_event(
                    event="email_resubscribed",
                    entity_type="email",
                    entity_id=email,
                    details={"removed_from_suppression": True}
                )
                
                logger.info(f"Email removed from suppression list: {email}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error removing email from suppression list: {e}")
            return False
    
    async def add_to_suppression_list(self, email: str, reason: str, source: str = "manual", 
                                     details: Dict = None) -> bool:
        """
        Add an email to the suppression list
        """
        try:
            email = email.lower().strip()
            
            # Check if already suppressed
            if await self.is_email_suppressed(email):
                logger.info(f"Email already suppressed: {email}")
                return True
            
            suppression_item = SuppressionList(
                email=email,
                reason=reason,
                source=source,
                details=details or {}
            )
            
            suppressions = self._load_suppression_list()
            suppressions.append(suppression_item)
            self._save_suppression_list(suppressions)
            
            log_business_event(
                event="email_suppressed",
                entity_type="email",
                entity_id=email,
                details={"reason": reason, "source": source}
            )
            
            logger.info(f"Email added to suppression list: {email}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding email to suppression list: {e}")
            return False
    
    async def get_suppression_list(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Get the current suppression list with pagination
        """
        try:
            suppressions = self._load_suppression_list()
            
            # Sort by added_at desc
            suppressions.sort(key=lambda x: x.added_at, reverse=True)
            
            # Apply pagination
            paginated = suppressions[offset:offset + limit]
            
            return [suppression.dict() for suppression in paginated]
            
        except Exception as e:
            logger.error(f"Error getting suppression list: {e}")
            return []
    
    async def get_unsubscribe_records(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Get unsubscribe records with pagination
        """
        try:
            records = self._load_unsubscribe_records()
            
            # Sort by unsubscribed_at desc
            records.sort(key=lambda x: x.unsubscribed_at, reverse=True)
            
            # Apply pagination
            paginated = records[offset:offset + limit]
            
            return [record.dict() for record in paginated]
            
        except Exception as e:
            logger.error(f"Error getting unsubscribe records: {e}")
            return []
    
    async def get_compliance_stats(self) -> Dict:
        """
        Get compliance statistics
        """
        try:
            suppressions = self._load_suppression_list()
            records = self._load_unsubscribe_records()
            
            # Count by reason
            suppression_reasons = {}
            for suppression in suppressions:
                reason = suppression.reason
                suppression_reasons[reason] = suppression_reasons.get(reason, 0) + 1
            
            # Recent unsubscribes (last 30 days)
            recent_unsubscribes = [
                r for r in records 
                if (datetime.utcnow() - r.unsubscribed_at).days <= 30
            ]
            
            return {
                "total_suppressed": len(suppressions),
                "total_unsubscribed": len([s for s in suppressions if s.reason == "unsubscribed"]),
                "total_bounced": len([s for s in suppressions if s.reason == "bounced"]),
                "total_complained": len([s for s in suppressions if s.reason == "complained"]),
                "suppression_reasons": suppression_reasons,
                "recent_unsubscribes": len(recent_unsubscribes),
                "unsubscribe_rate": self._calculate_unsubscribe_rate()
            }
            
        except Exception as e:
            logger.error(f"Error getting compliance stats: {e}")
            return {}
    
    def _calculate_unsubscribe_rate(self) -> float:
        """
        Calculate the unsubscribe rate based on recent email activity
        """
        try:
            # This would ideally calculate based on emails sent vs unsubscribes
            # For now, return a placeholder
            return 0.02  # 2% unsubscribe rate
            
        except Exception as e:
            logger.error(f"Error calculating unsubscribe rate: {e}")
            return 0.0
    
    async def filter_suppressed_emails(self, email_list: List[str]) -> List[str]:
        """
        Filter out suppressed emails from a list
        """
        try:
            suppressions = self._load_suppression_list()
            suppressed_emails = {s.email for s in suppressions}
            
            filtered_emails = [
                email.lower().strip() for email in email_list 
                if email.lower().strip() not in suppressed_emails
            ]
            
            filtered_count = len(email_list) - len(filtered_emails)
            if filtered_count > 0:
                logger.info(f"Filtered out {filtered_count} suppressed emails")
            
            return filtered_emails
            
        except Exception as e:
            logger.error(f"Error filtering suppressed emails: {e}")
            return email_list
    
    async def generate_unsubscribe_link(self, email: str, workflow_id: str = None, 
                                       template_id: str = None) -> str:
        """
        Generate a secure unsubscribe link
        """
        try:
            import base64
            import hashlib
            
            # Create a token with email and timestamp
            timestamp = str(int(datetime.utcnow().timestamp()))
            token_data = f"{email}:{timestamp}"
            
            # Create a hash for security
            secret = os.getenv("UNSUBSCRIBE_SECRET", "default_secret_key")
            hash_obj = hashlib.sha256(f"{token_data}:{secret}".encode())
            token_hash = hash_obj.hexdigest()[:16]
            
            # Encode the token
            token = base64.b64encode(f"{token_data}:{token_hash}".encode()).decode()
            
            # Build the unsubscribe URL
            base_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
            params = f"token={token}"
            
            if workflow_id:
                params += f"&workflow_id={workflow_id}"
            if template_id:
                params += f"&template_id={template_id}"
            
            unsubscribe_url = f"{base_url}/unsubscribe?{params}"
            
            return unsubscribe_url
            
        except Exception as e:
            logger.error(f"Error generating unsubscribe link: {e}")
            return f"http://localhost:3000/unsubscribe?email={email}"
    
    async def verify_unsubscribe_token(self, token: str) -> Optional[Dict]:
        """
        Verify an unsubscribe token and extract email
        """
        try:
            import base64
            import hashlib
            
            # Decode the token
            decoded = base64.b64decode(token.encode()).decode()
            parts = decoded.split(":")
            
            if len(parts) != 3:
                return None
            
            email, timestamp, token_hash = parts
            
            # Verify the hash
            secret = os.getenv("UNSUBSCRIBE_SECRET", "default_secret_key")
            expected_hash = hashlib.sha256(f"{email}:{timestamp}:{secret}".encode()).hexdigest()[:16]
            
            if token_hash != expected_hash:
                return None
            
            # Check if token is not too old (30 days)
            token_age = datetime.utcnow().timestamp() - float(timestamp)
            if token_age > 30 * 24 * 60 * 60:  # 30 days
                return None
            
            return {"email": email, "timestamp": timestamp}
            
        except Exception as e:
            logger.error(f"Error verifying unsubscribe token: {e}")
            return None
    
    def add_unsubscribe_footer(self, email_content: str, unsubscribe_link: str) -> str:
        """
        Add unsubscribe footer to email content
        """
        try:
            footer = f"""

---

You received this email because you signed up for AI Lead Gen updates.

If you no longer wish to receive these emails, you can unsubscribe here: {unsubscribe_link}

AI Lead Gen
support@aileadgen.dev
"""
            
            return email_content + footer
            
        except Exception as e:
            logger.error(f"Error adding unsubscribe footer: {e}")
            return email_content
    
    async def bulk_import_suppression_list(self, emails: List[str], reason: str = "imported") -> Dict:
        """
        Bulk import emails to suppression list
        """
        try:
            added_count = 0
            skipped_count = 0
            
            for email in emails:
                email = email.lower().strip()
                if not await self.is_email_suppressed(email):
                    await self.add_to_suppression_list(email, reason, "bulk_import")
                    added_count += 1
                else:
                    skipped_count += 1
            
            return {
                "added": added_count,
                "skipped": skipped_count,
                "total": len(emails)
            }
            
        except Exception as e:
            logger.error(f"Error bulk importing suppression list: {e}")
            return {"added": 0, "skipped": 0, "total": len(emails), "error": str(e)}