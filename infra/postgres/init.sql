-- PostgreSQL Database Initialization Script for NIDAN AI
-- Enables necessary extensions for UUIDs, JSON querying, and cryptographic hashing

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Grant privileges if needed
GRANT ALL PRIVILEGES ON DATABASE nidan_ai TO nidan_user;
