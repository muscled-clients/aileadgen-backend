from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class Niche(BaseModel):
    niche_id: Optional[int] = None
    name: str
    slug: str
    active: bool = True
    created_at: Optional[datetime] = None

class LandingPage(BaseModel):
    page_id: Optional[int] = None
    niche_id: int
    headline: str
    subheadline: str
    video_url: Optional[str] = None
    cta_text: str
    is_active: bool = True
    created_at: Optional[datetime] = None

class PainPoint(BaseModel):
    pain_id: Optional[int] = None
    niche_id: int
    title: str
    description: str
    icon: Optional[str] = None
    display_order: int = 0
    created_at: Optional[datetime] = None

class SocialProof(BaseModel):
    proof_id: Optional[int] = None
    niche_id: int
    stat_number: str
    stat_text: str
    display_order: int = 0
    created_at: Optional[datetime] = None

class Testimonial(BaseModel):
    testimonial_id: Optional[int] = None
    niche_id: int
    name: str
    company: Optional[str] = None
    text: str
    image_url: Optional[str] = None
    result_metric: Optional[str] = None
    display_order: int = 0
    created_at: Optional[datetime] = None

class CTAOffer(BaseModel):
    offer_id: Optional[int] = None
    niche_id: int
    offer_title: str
    benefits: List[str]
    guarantee_text: Optional[str] = None
    button_text: str
    created_at: Optional[datetime] = None

class LandingPageData(BaseModel):
    niche: Niche
    landing_page: LandingPage
    pain_points: List[PainPoint]
    social_proof: List[SocialProof]
    testimonials: List[Testimonial]
    cta_offer: CTAOffer

class LeadQualificationForm(BaseModel):
    name: str
    email: str
    phone: str
    business_type: str
    monthly_revenue: str
    marketing_budget: str
    biggest_challenge: str
    niche_slug: str
    qualified: bool = False