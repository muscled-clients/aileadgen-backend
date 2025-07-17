"""
Lead Segmentation Service - Advanced targeting for email automation
Handles lead filtering, segmentation, and targeting based on various criteria
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from services.simple_lead_service import SimpleLeadService
from utils.logger import logger, log_business_event

class LeadSegment:
    """Represents a lead segment with filtering criteria"""
    
    def __init__(self, name: str, criteria: Dict[str, Any]):
        self.name = name
        self.criteria = criteria
        self.created_at = datetime.utcnow()
        
    def matches_lead(self, lead: Dict[str, Any]) -> bool:
        """Check if a lead matches this segment's criteria"""
        try:
            for key, value in self.criteria.items():
                if key == "qualified" and lead.get("qualified") != value:
                    return False
                elif key == "niche" and lead.get("niche") != value:
                    return False
                elif key == "source" and lead.get("source") != value:
                    return False
                elif key == "completion_status" and lead.get("completion_status") != value:
                    return False
                elif key == "revenue_min":
                    revenue = lead.get("monthly_revenue", "")
                    if not self._meets_revenue_threshold(revenue, value):
                        return False
                elif key == "revenue_max":
                    revenue = lead.get("monthly_revenue", "")
                    if not self._below_revenue_threshold(revenue, value):
                        return False
                elif key == "budget_min":
                    budget = lead.get("marketing_budget", "")
                    if not self._meets_budget_threshold(budget, value):
                        return False
                elif key == "created_after":
                    created_at = datetime.fromisoformat(lead.get("created_at", ""))
                    if created_at < value:
                        return False
                elif key == "created_before":
                    created_at = datetime.fromisoformat(lead.get("created_at", ""))
                    if created_at > value:
                        return False
                elif key == "pain_points" and isinstance(value, list):
                    lead_pain_point = lead.get("pain_point", "")
                    if not any(pain in lead_pain_point.lower() for pain in value):
                        return False
                elif key == "exclude_email_sent":
                    # This would check if lead has received specific emails
                    # Implementation would check email history
                    pass
                    
            return True
            
        except Exception as e:
            logger.error(f"Error matching lead to segment: {e}")
            return False
    
    def _meets_revenue_threshold(self, revenue: str, threshold: int) -> bool:
        """Check if revenue meets minimum threshold"""
        try:
            # Parse revenue ranges like "$40K - $80K"
            if "K" in revenue:
                # Extract first number
                revenue_num = int(revenue.split("K")[0].split("$")[-1].strip())
                return revenue_num >= threshold
            return False
        except:
            return False
    
    def _below_revenue_threshold(self, revenue: str, threshold: int) -> bool:
        """Check if revenue is below maximum threshold"""
        try:
            if "K" in revenue:
                revenue_num = int(revenue.split("K")[0].split("$")[-1].strip())
                return revenue_num <= threshold
            return False
        except:
            return False
    
    def _meets_budget_threshold(self, budget: str, threshold: int) -> bool:
        """Check if budget meets minimum threshold"""
        try:
            if "K" in budget:
                budget_num = int(budget.split("K")[0].split("$")[-1].strip())
                return budget_num >= threshold
            return False
        except:
            return False

class LeadSegmentationService:
    """Service for managing lead segmentation and targeting"""
    
    def __init__(self):
        self.lead_service = SimpleLeadService()
        self.predefined_segments = self._create_predefined_segments()
    
    def _create_predefined_segments(self) -> Dict[str, LeadSegment]:
        """Create commonly used lead segments"""
        return {
            "all_leads": LeadSegment("All Leads", {}),
            "qualified_leads": LeadSegment("Qualified Leads", {"qualified": True}),
            "unqualified_leads": LeadSegment("Unqualified Leads", {"qualified": False}),
            "complete_leads": LeadSegment("Complete Leads", {"completion_status": "complete"}),
            "incomplete_leads": LeadSegment("Incomplete Leads", {"completion_status": "incomplete"}),
            "real_estate_leads": LeadSegment("Real Estate Leads", {"niche": "real-estate"}),
            "dental_leads": LeadSegment("Dental Leads", {"niche": "dental"}),
            "high_revenue_leads": LeadSegment("High Revenue Leads ($40K+)", {"revenue_min": 40, "qualified": True}),
            "premium_leads": LeadSegment("Premium Leads ($80K+)", {"revenue_min": 80, "qualified": True}),
            "landing_page_leads": LeadSegment("Landing Page Leads", {"source": "landing_page"}),
            "call_system_leads": LeadSegment("Call System Leads", {"source": "call_system"}),
            "recent_leads": LeadSegment("Recent Leads (Last 7 Days)", {
                "created_after": datetime.utcnow() - timedelta(days=7)
            }),
            "older_leads": LeadSegment("Older Leads (30+ Days)", {
                "created_before": datetime.utcnow() - timedelta(days=30)
            }),
            "high_budget_leads": LeadSegment("High Budget Leads ($5K+)", {"budget_min": 5, "qualified": True}),
            "lead_generation_pain": LeadSegment("Lead Generation Pain Point", {
                "pain_points": ["leads", "lead generation", "not enough leads"],
                "qualified": True
            }),
            "quality_leads_pain": LeadSegment("Quality Leads Pain Point", {
                "pain_points": ["quality", "poor quality", "low quality"],
                "qualified": True
            })
        }
    
    async def get_segment_by_name(self, segment_name: str) -> Optional[LeadSegment]:
        """Get a predefined segment by name"""
        return self.predefined_segments.get(segment_name)
    
    async def get_available_segments(self) -> List[Dict[str, Any]]:
        """Get all available segments with descriptions"""
        segments = []
        for key, segment in self.predefined_segments.items():
            segments.append({
                "key": key,
                "name": segment.name,
                "criteria": segment.criteria,
                "description": self._get_segment_description(key)
            })
        return segments
    
    def _get_segment_description(self, segment_key: str) -> str:
        """Get description for a segment"""
        descriptions = {
            "all_leads": "All leads in the system",
            "qualified_leads": "Leads that meet revenue and budget requirements",
            "unqualified_leads": "Leads that don't meet qualification criteria",
            "complete_leads": "Leads that completed the entire form",
            "incomplete_leads": "Leads that didn't complete the form",
            "real_estate_leads": "Leads in the real estate niche",
            "dental_leads": "Leads in the dental niche",
            "high_revenue_leads": "Qualified leads with $40K+ monthly revenue",
            "premium_leads": "Qualified leads with $80K+ monthly revenue",
            "landing_page_leads": "Leads from landing page forms",
            "call_system_leads": "Leads from the call system",
            "recent_leads": "Leads created in the last 7 days",
            "older_leads": "Leads created more than 30 days ago",
            "high_budget_leads": "Qualified leads with $5K+ marketing budget",
            "lead_generation_pain": "Leads with lead generation pain points",
            "quality_leads_pain": "Leads with lead quality pain points"
        }
        return descriptions.get(segment_key, "Custom segment")
    
    async def get_leads_by_segment(self, segment_name: str) -> List[Dict[str, Any]]:
        """Get all leads that match a specific segment"""
        try:
            segment = await self.get_segment_by_name(segment_name)
            if not segment:
                logger.error(f"Segment not found: {segment_name}")
                return []
            
            # Get all leads
            all_leads = await self.lead_service.get_leads(skip=0, limit=10000)
            
            # Filter leads by segment criteria
            matching_leads = []
            for lead in all_leads:
                if segment.matches_lead(lead.dict()):
                    matching_leads.append(lead.dict())
            
            log_business_event(
                event="segment_filtered",
                entity_type="segment",
                entity_id=segment_name,
                details={"total_leads": len(all_leads), "matching_leads": len(matching_leads)}
            )
            
            logger.info(f"Found {len(matching_leads)} leads for segment: {segment_name}")
            return matching_leads
            
        except Exception as e:
            logger.error(f"Error getting leads by segment: {e}")
            return []
    
    async def create_custom_segment(self, name: str, criteria: Dict[str, Any]) -> LeadSegment:
        """Create a custom segment with specific criteria"""
        try:
            segment = LeadSegment(name, criteria)
            
            log_business_event(
                event="custom_segment_created",
                entity_type="segment",
                entity_id=name,
                details={"criteria": criteria}
            )
            
            logger.info(f"Created custom segment: {name}")
            return segment
            
        except Exception as e:
            logger.error(f"Error creating custom segment: {e}")
            raise
    
    async def get_segment_stats(self, segment_name: str) -> Dict[str, Any]:
        """Get statistics for a specific segment"""
        try:
            leads = await self.get_leads_by_segment(segment_name)
            
            stats = {
                "total_leads": len(leads),
                "qualified_leads": len([l for l in leads if l.get("qualified", False)]),
                "complete_leads": len([l for l in leads if l.get("completion_status") == "complete"]),
                "niche_breakdown": {},
                "source_breakdown": {},
                "revenue_breakdown": {},
                "recent_leads": len([l for l in leads if 
                    datetime.fromisoformat(l.get("created_at", "")) > datetime.utcnow() - timedelta(days=7)
                ])
            }
            
            # Calculate breakdowns
            for lead in leads:
                # Niche breakdown
                niche = lead.get("niche", "unknown")
                stats["niche_breakdown"][niche] = stats["niche_breakdown"].get(niche, 0) + 1
                
                # Source breakdown
                source = lead.get("source", "unknown")
                stats["source_breakdown"][source] = stats["source_breakdown"].get(source, 0) + 1
                
                # Revenue breakdown
                revenue = lead.get("monthly_revenue", "unknown")
                stats["revenue_breakdown"][revenue] = stats["revenue_breakdown"].get(revenue, 0) + 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting segment stats: {e}")
            return {}
    
    async def filter_leads_for_workflow(self, workflow_criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter leads based on workflow targeting criteria"""
        try:
            target_audience = workflow_criteria.get("target_audience", "all_leads")
            
            # Get leads by segment
            leads = await self.get_leads_by_segment(target_audience)
            
            # Apply additional workflow-specific filters
            if workflow_criteria.get("exclude_recent_emails"):
                # Filter out leads that received emails recently
                # This would integrate with email history
                pass
            
            if workflow_criteria.get("min_days_since_last_email"):
                # Filter based on last email sent
                # This would integrate with email history
                pass
            
            return leads
            
        except Exception as e:
            logger.error(f"Error filtering leads for workflow: {e}")
            return []
    
    async def get_segment_preview(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Preview how many leads would match given criteria"""
        try:
            # Create temporary segment
            temp_segment = LeadSegment("Preview", criteria)
            
            # Get all leads
            all_leads = await self.lead_service.get_leads(skip=0, limit=10000)
            
            # Count matches
            matching_count = 0
            for lead in all_leads:
                if temp_segment.matches_lead(lead.dict()):
                    matching_count += 1
            
            return {
                "total_leads": len(all_leads),
                "matching_leads": matching_count,
                "match_percentage": round((matching_count / len(all_leads)) * 100, 2) if all_leads else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting segment preview: {e}")
            return {"total_leads": 0, "matching_leads": 0, "match_percentage": 0}
    
    async def analyze_segment_performance(self, segment_name: str) -> Dict[str, Any]:
        """Analyze email performance for a specific segment"""
        try:
            # This would integrate with email history to analyze performance
            # For now, return placeholder data
            return {
                "segment_name": segment_name,
                "total_emails_sent": 0,
                "open_rate": 0.0,
                "click_rate": 0.0,
                "conversion_rate": 0.0,
                "best_performing_templates": [],
                "worst_performing_templates": []
            }
            
        except Exception as e:
            logger.error(f"Error analyzing segment performance: {e}")
            return {}