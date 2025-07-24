-- Database initialization script for Warehouse AI Agent
-- This script creates the necessary tables and initial data

-- Create warehouse_pallets table
CREATE TABLE IF NOT EXISTS warehouse_pallets (
    id SERIAL PRIMARY KEY,
    pallet_id VARCHAR(50) UNIQUE NOT NULL,
    po_id VARCHAR(50) NOT NULL,
    asn_id VARCHAR(50),
    quantity INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    location VARCHAR(100),
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_date TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_warehouse_pallets_po_id ON warehouse_pallets(po_id);
CREATE INDEX IF NOT EXISTS idx_warehouse_pallets_asn_id ON warehouse_pallets(asn_id);
CREATE INDEX IF NOT EXISTS idx_warehouse_pallets_status ON warehouse_pallets(status);
CREATE INDEX IF NOT EXISTS idx_warehouse_pallets_created_date ON warehouse_pallets(created_date);

-- Create audit log table
CREATE TABLE IF NOT EXISTS warehouse_audit_log (
    id SERIAL PRIMARY KEY,
    issue_id VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    details TEXT,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for audit log
CREATE INDEX IF NOT EXISTS idx_audit_log_issue_id ON warehouse_audit_log(issue_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_date ON warehouse_audit_log(created_date);

-- Insert sample data for testing
INSERT INTO warehouse_pallets (pallet_id, po_id, asn_id, quantity, status, location) VALUES
    ('PLT001', 'PO12345', 'ASN67890', 100, 'ACTIVE', 'A-01-01'),
    ('PLT002', 'PO12345', 'ASN67890', 150, 'ACTIVE', 'A-01-02'),
    ('PLT003', 'PO12345', 'ASN67890', 200, 'ACTIVE', 'A-01-03'),
    ('PLT004', 'PO12346', 'ASN67891', 75, 'ACTIVE', 'B-02-01'),
    ('PLT005', 'PO12346', 'ASN67891', 125, 'ACTIVE', 'B-02-02'),
    ('PLT006', 'PO12347', 'ASN67892', 300, 'ACTIVE', 'C-03-01'),
    ('PLT007', 'PO12347', 'ASN67892', 250, 'ACTIVE', 'C-03-02'),
    ('PLT008', 'PO12348', 'ASN67893', 180, 'ACTIVE', 'D-04-01'),
    ('PLT009', 'PO12348', 'ASN67893', 220, 'ACTIVE', 'D-04-02'),
    ('PLT010', 'PO12349', 'ASN67894', 160, 'ACTIVE', 'E-05-01')
ON CONFLICT (pallet_id) DO NOTHING;

-- Create a view for PO summaries
CREATE OR REPLACE VIEW po_summary_view AS
SELECT 
    po_id,
    COUNT(*) as pallet_count,
    SUM(quantity) as total_quantity,
    COUNT(DISTINCT asn_id) as asn_count,
    MIN(created_date) as first_created,
    MAX(updated_date) as last_updated
FROM warehouse_pallets 
WHERE status = 'ACTIVE'
GROUP BY po_id;

-- Create a function to get PO summary (PostgreSQL specific)
CREATE OR REPLACE FUNCTION get_po_summary(p_po_id VARCHAR)
RETURNS TABLE(
    po_id VARCHAR,
    pallet_count BIGINT,
    total_quantity BIGINT,
    asn_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p_po_id::VARCHAR,
        COUNT(*)::BIGINT,
        SUM(wp.quantity)::BIGINT,
        COUNT(DISTINCT wp.asn_id)::BIGINT
    FROM warehouse_pallets wp
    WHERE wp.po_id = p_po_id AND wp.status = 'ACTIVE';
END;
$$ LANGUAGE plpgsql;

-- Create a function to insert missing pallets
CREATE OR REPLACE FUNCTION insert_missing_pallet(
    p_pallet_id VARCHAR,
    p_po_id VARCHAR,
    p_asn_id VARCHAR,
    p_quantity INTEGER,
    p_status VARCHAR DEFAULT 'ACTIVE',
    p_location VARCHAR DEFAULT NULL
) RETURNS BOOLEAN AS $$
BEGIN
    INSERT INTO warehouse_pallets (pallet_id, po_id, asn_id, quantity, status, location)
    VALUES (p_pallet_id, p_po_id, p_asn_id, p_quantity, p_status, p_location)
    ON CONFLICT (pallet_id) DO UPDATE SET
        quantity = EXCLUDED.quantity,
        status = EXCLUDED.status,
        location = EXCLUDED.location,
        updated_date = CURRENT_TIMESTAMP;
    
    RETURN TRUE;
EXCEPTION
    WHEN OTHERS THEN
        RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions to the warehouse user
GRANT SELECT, INSERT, UPDATE, DELETE ON warehouse_pallets TO warehouse_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON warehouse_audit_log TO warehouse_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO warehouse_user;
GRANT SELECT ON po_summary_view TO warehouse_user;

-- Insert initial audit log entry
INSERT INTO warehouse_audit_log (issue_id, action, details) VALUES
    ('SYSTEM_INIT', 'DATABASE_INITIALIZED', 'Database tables and sample data created successfully');

COMMIT;