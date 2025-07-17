-- AI Caller MVP Database Schema

-- Create leads table
CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    timezone TEXT DEFAULT 'UTC',
    status TEXT DEFAULT 'new' CHECK (status IN ('new', 'called', 'booked', 'callback', 'not_answered', 'failed')),
    last_call_time TIMESTAMP WITH TIME ZONE,
    notes TEXT DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create call_logs table
CREATE TABLE IF NOT EXISTS call_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    outcome TEXT CHECK (outcome IN ('booked', 'not_answered', 'callback', 'failed', 'completed', 'busy')),
    transcript JSONB DEFAULT '[]',
    recording_url TEXT,
    duration_sec INTEGER,
    ai_agent_version TEXT DEFAULT '1.0.0',
    status TEXT DEFAULT 'pending',
    call_sid TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at);
CREATE INDEX IF NOT EXISTS idx_leads_phone_number ON leads(phone_number);

CREATE INDEX IF NOT EXISTS idx_call_logs_lead_id ON call_logs(lead_id);
CREATE INDEX IF NOT EXISTS idx_call_logs_timestamp ON call_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_call_logs_outcome ON call_logs(outcome);
CREATE INDEX IF NOT EXISTS idx_call_logs_call_sid ON call_logs(call_sid);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_leads_updated_at BEFORE UPDATE ON leads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_call_logs_updated_at BEFORE UPDATE ON call_logs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (RLS)
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_logs ENABLE ROW LEVEL SECURITY;

-- Create RLS policies (adjust based on your auth requirements)
CREATE POLICY "Enable read access for all users" ON leads FOR SELECT USING (true);
CREATE POLICY "Enable insert for all users" ON leads FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for all users" ON leads FOR UPDATE USING (true);
CREATE POLICY "Enable delete for all users" ON leads FOR DELETE USING (true);

CREATE POLICY "Enable read access for all users" ON call_logs FOR SELECT USING (true);
CREATE POLICY "Enable insert for all users" ON call_logs FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for all users" ON call_logs FOR UPDATE USING (true);
CREATE POLICY "Enable delete for all users" ON call_logs FOR DELETE USING (true);

-- Create storage bucket for call recordings
INSERT INTO storage.buckets (id, name, public) VALUES ('call-recordings', 'call-recordings', true);

-- Create storage policy for call recordings
CREATE POLICY "Enable read access for all users" ON storage.objects FOR SELECT USING (bucket_id = 'call-recordings');
CREATE POLICY "Enable insert for all users" ON storage.objects FOR INSERT WITH CHECK (bucket_id = 'call-recordings');
CREATE POLICY "Enable update for all users" ON storage.objects FOR UPDATE USING (bucket_id = 'call-recordings');
CREATE POLICY "Enable delete for all users" ON storage.objects FOR DELETE USING (bucket_id = 'call-recordings');

-- Sample data for testing
INSERT INTO leads (name, phone_number, timezone, status, notes) VALUES 
('John Doe', '+1234567890', 'America/New_York', 'new', 'Interested in our services'),
('Jane Smith', '+1987654321', 'America/Los_Angeles', 'new', 'Referred by existing customer'),
('Mike Johnson', '+1122334455', 'America/Chicago', 'called', 'Had initial conversation');

-- Create a view for dashboard stats
CREATE OR REPLACE VIEW dashboard_stats AS
SELECT 
    COUNT(*) as total_leads,
    COUNT(CASE WHEN status = 'new' THEN 1 END) as new_leads,
    COUNT(CASE WHEN status = 'called' THEN 1 END) as called_leads,
    COUNT(CASE WHEN status = 'booked' THEN 1 END) as booked_leads,
    COUNT(CASE WHEN status = 'callback' THEN 1 END) as callback_leads,
    COUNT(CASE WHEN status = 'not_answered' THEN 1 END) as not_answered_leads,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_leads
FROM leads;

-- Create a view for call analytics
CREATE OR REPLACE VIEW call_analytics AS
SELECT 
    DATE(timestamp) as call_date,
    COUNT(*) as total_calls,
    COUNT(CASE WHEN outcome = 'booked' THEN 1 END) as booked_calls,
    COUNT(CASE WHEN outcome = 'not_answered' THEN 1 END) as not_answered_calls,
    COUNT(CASE WHEN outcome = 'callback' THEN 1 END) as callback_calls,
    COUNT(CASE WHEN outcome = 'failed' THEN 1 END) as failed_calls,
    AVG(duration_sec) as avg_duration_sec
FROM call_logs
GROUP BY DATE(timestamp)
ORDER BY call_date DESC;