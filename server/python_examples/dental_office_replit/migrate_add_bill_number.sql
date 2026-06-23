-- Migration: Add bill_number column to billing table
-- This adds a unique 6-digit bill number for each bill

-- Add the bill_number column (without UNIQUE constraint first)
ALTER TABLE billing ADD COLUMN bill_number TEXT;

-- Generate 6-digit bill numbers for existing records
-- Using a deterministic approach based on the row ID
UPDATE billing 
SET bill_number = CAST(
    (100000 + (id * 13 + 37) % 900000) AS TEXT
) 
WHERE bill_number IS NULL;

-- Now create a unique index (equivalent to UNIQUE constraint)
CREATE UNIQUE INDEX idx_billing_bill_number ON billing(bill_number); 