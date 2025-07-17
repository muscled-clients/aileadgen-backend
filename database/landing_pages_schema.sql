-- Multi-Niche Landing Page Database Schema

-- Niches table for different industries
CREATE TABLE niches (
    niche_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Landing pages for each niche
CREATE TABLE landing_pages (
    page_id SERIAL PRIMARY KEY,
    niche_id INTEGER REFERENCES niches(niche_id),
    headline TEXT NOT NULL,
    subheadline TEXT NOT NULL,
    video_url TEXT,
    cta_text VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Pain points specific to each niche
CREATE TABLE pain_points (
    pain_id SERIAL PRIMARY KEY,
    niche_id INTEGER REFERENCES niches(niche_id),
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    icon VARCHAR(50),
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Social proof stats for each niche
CREATE TABLE social_proof (
    proof_id SERIAL PRIMARY KEY,
    niche_id INTEGER REFERENCES niches(niche_id),
    stat_number VARCHAR(50) NOT NULL,
    stat_text TEXT NOT NULL,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Testimonials for each niche
CREATE TABLE testimonials (
    testimonial_id SERIAL PRIMARY KEY,
    niche_id INTEGER REFERENCES niches(niche_id),
    name VARCHAR(100) NOT NULL,
    company VARCHAR(100),
    text TEXT NOT NULL,
    image_url TEXT,
    result_metric VARCHAR(100),
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- CTA offers for each niche
CREATE TABLE cta_offers (
    offer_id SERIAL PRIMARY KEY,
    niche_id INTEGER REFERENCES niches(niche_id),
    offer_title VARCHAR(200) NOT NULL,
    benefits TEXT[] NOT NULL,
    guarantee_text TEXT,
    button_text VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample data for Real Estate niche
INSERT INTO niches (name, slug) VALUES ('Real Estate', 'real-estate');

-- Get the niche_id for real estate
DO $$
DECLARE
    real_estate_id INTEGER;
BEGIN
    SELECT niche_id INTO real_estate_id FROM niches WHERE slug = 'real-estate';
    
    -- Insert landing page data for real estate
    INSERT INTO landing_pages (niche_id, headline, subheadline, video_url, cta_text)
    VALUES (
        real_estate_id,
        'Stop Chasing Cold Leads - Get Ready-to-Buy Clients Calling You',
        'Our AI calls 500+ prospects daily and only sends you qualified buyers with $500K+ budgets',
        'https://example.com/real-estate-demo-video',
        'Get My First 10 Qualified Buyers FREE'
    );
    
    -- Insert pain points for real estate
    INSERT INTO pain_points (niche_id, title, description, icon, display_order) VALUES
    (real_estate_id, 'Spending $3K/month on Zillow leads that never convert', 'You''re paying premium prices for leads that 20 other agents are also calling', 'money-off', 1),
    (real_estate_id, 'Competing with 50+ agents for the same tired leads', 'Every lead source is oversaturated with desperate agents fighting for scraps', 'users', 2),
    (real_estate_id, 'Wasting hours calling prospects who aren''t ready to buy', 'Most leads are just browsing or won''t be ready for 6-12 months', 'clock', 3);
    
    -- Insert social proof for real estate
    INSERT INTO social_proof (niche_id, stat_number, stat_text, display_order) VALUES
    (real_estate_id, '2,847', 'Qualified Buyers Connected This Month', 1),
    (real_estate_id, '87%', 'Of Our Leads Are Ready to Buy Within 30 Days', 2),
    (real_estate_id, '$2.3M', 'Average Commission Generated Per Agent Monthly', 3);
    
    -- Insert testimonials for real estate
    INSERT INTO testimonials (niche_id, name, company, text, result_metric, display_order) VALUES
    (real_estate_id, 'Sarah Johnson', 'Keller Williams', 'I went from 2 closings per month to 8 closings per month. The AI only sends me buyers who are pre-qualified and ready to move forward.', 'Closed 12 deals in 60 days', 1),
    (real_estate_id, 'Mike Rodriguez', 'RE/MAX', 'This completely changed my business. I used to spend 4 hours daily cold calling. Now I spend that time with actual buyers viewing properties.', 'Increased income by 300%', 2),
    (real_estate_id, 'Jennifer Chen', 'Coldwell Banker', 'The best investment I''ve ever made. The AI brings me qualified leads while I focus on what I do best - closing deals.', 'Generated $1.2M in commissions', 3);
    
    -- Insert CTA offer for real estate
    INSERT INTO cta_offers (niche_id, offer_title, benefits, guarantee_text, button_text) VALUES
    (real_estate_id, 'Get Your First 10 Qualified Buyers FREE', 
     ARRAY[
         'Custom AI trained specifically for your market area',
         '500+ calls made in first 48 hours',
         'Only pre-qualified buyers with $500K+ budgets',
         'Appointments booked directly to your calendar',
         'No setup fees or hidden costs'
     ],
     'If you don''t get at least 5 qualified appointments in 30 days, we''ll refund everything and pay you $500 for your time',
     'Claim My 10 Free Qualified Buyers Now'
    );
END $$;