from typing import Dict, List, Optional
import asyncpg
import os
from models.landing_page_models import *

class LandingPageService:
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/ai_lead_gen")
    
    async def get_connection(self):
        """Get database connection"""
        return await asyncpg.connect(self.db_url)
    
    async def get_landing_page_data(self, niche_slug: str) -> Optional[LandingPageData]:
        """Get all landing page data for a specific niche"""
        conn = await self.get_connection()
        try:
            # Get niche
            niche_row = await conn.fetchrow(
                "SELECT * FROM niches WHERE slug = $1 AND active = true", 
                niche_slug
            )
            if not niche_row:
                return None
            
            niche = Niche(**dict(niche_row))
            
            # Get landing page
            landing_page_row = await conn.fetchrow(
                "SELECT * FROM landing_pages WHERE niche_id = $1 AND is_active = true",
                niche.niche_id
            )
            if not landing_page_row:
                return None
            
            landing_page = LandingPage(**dict(landing_page_row))
            
            # Get pain points
            pain_points_rows = await conn.fetch(
                "SELECT * FROM pain_points WHERE niche_id = $1 ORDER BY display_order",
                niche.niche_id
            )
            pain_points = [PainPoint(**dict(row)) for row in pain_points_rows]
            
            # Get social proof
            social_proof_rows = await conn.fetch(
                "SELECT * FROM social_proof WHERE niche_id = $1 ORDER BY display_order",
                niche.niche_id
            )
            social_proof = [SocialProof(**dict(row)) for row in social_proof_rows]
            
            # Get testimonials
            testimonials_rows = await conn.fetch(
                "SELECT * FROM testimonials WHERE niche_id = $1 ORDER BY display_order",
                niche.niche_id
            )
            testimonials = [Testimonial(**dict(row)) for row in testimonials_rows]
            
            # Get CTA offer
            cta_offer_row = await conn.fetchrow(
                "SELECT * FROM cta_offers WHERE niche_id = $1",
                niche.niche_id
            )
            if not cta_offer_row:
                return None
            
            cta_offer = CTAOffer(**dict(cta_offer_row))
            
            return LandingPageData(
                niche=niche,
                landing_page=landing_page,
                pain_points=pain_points,
                social_proof=social_proof,
                testimonials=testimonials,
                cta_offer=cta_offer
            )
            
        finally:
            await conn.close()
    
    async def get_all_niches(self) -> List[Niche]:
        """Get all active niches"""
        conn = await self.get_connection()
        try:
            rows = await conn.fetch("SELECT * FROM niches WHERE active = true ORDER BY name")
            return [Niche(**dict(row)) for row in rows]
        finally:
            await conn.close()
    
    async def create_niche(self, niche: Niche) -> Niche:
        """Create a new niche"""
        conn = await self.get_connection()
        try:
            row = await conn.fetchrow(
                "INSERT INTO niches (name, slug, active) VALUES ($1, $2, $3) RETURNING *",
                niche.name, niche.slug, niche.active
            )
            return Niche(**dict(row))
        finally:
            await conn.close()
    
    async def update_landing_page(self, page_id: int, landing_page: LandingPage) -> LandingPage:
        """Update landing page content"""
        conn = await self.get_connection()
        try:
            row = await conn.fetchrow(
                """UPDATE landing_pages 
                   SET headline = $1, subheadline = $2, video_url = $3, cta_text = $4
                   WHERE page_id = $5 RETURNING *""",
                landing_page.headline, landing_page.subheadline, 
                landing_page.video_url, landing_page.cta_text, page_id
            )
            return LandingPage(**dict(row))
        finally:
            await conn.close()
    
    async def create_pain_point(self, pain_point: PainPoint) -> PainPoint:
        """Create a new pain point"""
        conn = await self.get_connection()
        try:
            row = await conn.fetchrow(
                """INSERT INTO pain_points (niche_id, title, description, icon, display_order)
                   VALUES ($1, $2, $3, $4, $5) RETURNING *""",
                pain_point.niche_id, pain_point.title, pain_point.description,
                pain_point.icon, pain_point.display_order
            )
            return PainPoint(**dict(row))
        finally:
            await conn.close()
    
    async def save_lead_qualification(self, form_data: LeadQualificationForm) -> bool:
        """Save lead qualification form data"""
        conn = await self.get_connection()
        try:
            await conn.execute(
                """INSERT INTO lead_qualifications 
                   (name, email, phone, business_type, monthly_revenue, marketing_budget, 
                    biggest_challenge, niche_slug, qualified, created_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())""",
                form_data.name, form_data.email, form_data.phone, form_data.business_type,
                form_data.monthly_revenue, form_data.marketing_budget, form_data.biggest_challenge,
                form_data.niche_slug, form_data.qualified
            )
            return True
        except Exception as e:
            print(f"Error saving lead qualification: {e}")
            return False
        finally:
            await conn.close()
    
    def qualify_lead(self, form_data: LeadQualificationForm) -> bool:
        """Determine if lead is qualified based on answers"""
        # Qualification logic
        revenue_qualified = form_data.monthly_revenue in ["$10K-$50K", "$50K-$100K", "$100K+"]
        budget_qualified = form_data.marketing_budget in ["$1K-$5K", "$5K-$10K", "$10K+"]
        business_qualified = form_data.business_type in ["Real Estate", "Insurance", "Legal", "Medical"]
        
        return revenue_qualified and budget_qualified and business_qualified