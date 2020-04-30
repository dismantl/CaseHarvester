-- executed as mjcs_user connected to mjcs database

CREATE SCHEMA IF NOT EXISTS redacted;

-- Create roles and users
CREATE ROLE mjcs_ro;
CREATE ROLE mjcs_ro_redacted;
CREATE USER ojb_public NOCREATEDB LOGIN NOSUPERUSER PASSWORD 'md51b9fcca3574af5a7b282118f020d6682';
GRANT mjcs_ro_redacted TO ojb_public;

-- Database level permissions
REVOKE ALL ON DATABASE mjcs FROM PUBLIC;
GRANT TEMPORARY, CONNECT ON DATABASE mjcs TO PUBLIC;

-- Schema level permissions
REVOKE ALL ON SCHEMA public, redacted FROM PUBLIC;
GRANT USAGE ON SCHEMA public, redacted TO mjcs_ro, mjcs_ro_redacted;

-- Table level permissions
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mjcs_ro, mjcs_ro_redacted;
GRANT SELECT ON ALL TABLES IN SCHEMA redacted TO mjcs_ro, mjcs_ro_redacted;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO mjcs_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA redacted
    GRANT SELECT ON TABLES TO mjcs_ro_redacted;

-- Redacted views
REVOKE SELECT ON TABLE public.cc_defendants FROM mjcs_ro_redacted;
CREATE OR REPLACE VIEW redacted.cc_defendants
 AS
 SELECT cc_defendants.id,
    cc_defendants.party_type,
    cc_defendants.party_number,
    cc_defendants.business_org_name,
    cc_defendants.case_number
   FROM cc_defendants;

REVOKE SELECT ON TABLE public.dscivil_complaints FROM mjcs_ro_redacted;
CREATE OR REPLACE VIEW redacted.dscivil_complaints
 AS
 SELECT dscivil_complaints.id,
    dscivil_complaints.complaint_number,
    dscivil_complaints.plaintiff,
    dscivil_complaints.complaint_type,
    dscivil_complaints.complaint_status,
    dscivil_complaints.status_date,
    dscivil_complaints.status_date_str,
    dscivil_complaints.filing_date,
    dscivil_complaints.filing_date_str,
    dscivil_complaints.amount,
    dscivil_complaints.last_activity_date,
    dscivil_complaints.last_activity_date_str,
    dscivil_complaints.case_number
   FROM dscivil_complaints;

REVOKE SELECT ON TABLE public.dscr_defendants FROM mjcs_ro_redacted;
CREATE OR REPLACE VIEW redacted.dscr_defendants
 AS
 SELECT dscr_defendants.id,
    dscr_defendants.race,
    dscr_defendants.sex,
    dscr_defendants.height,
    dscr_defendants.weight,
    dscr_defendants.city,
    dscr_defendants.state,
    dscr_defendants.zip_code,
    dscr_defendants.case_number
   FROM dscr_defendants;

REVOKE SELECT ON TABLE public.dsk8_defendants FROM mjcs_ro_redacted;
CREATE OR REPLACE VIEW redacted.dsk8_defendants
 AS
 SELECT dsk8_defendants.id,
    dsk8_defendants.race,
    dsk8_defendants.sex,
    dsk8_defendants.height,
    dsk8_defendants.weight,
    dsk8_defendants.city,
    dsk8_defendants.state,
    dsk8_defendants.zip_code,
    dsk8_defendants.case_number
   FROM dsk8_defendants;

REVOKE SELECT ON TABLE public.odycrim_defendants FROM mjcs_ro_redacted;
CREATE OR REPLACE VIEW redacted.odycrim_defendants
 AS
 SELECT odycrim_defendants.id,
    odycrim_defendants.race,
    odycrim_defendants.sex,
    odycrim_defendants.weight,
    odycrim_defendants.city,
    odycrim_defendants.state,
    odycrim_defendants.zip_code,
    odycrim_defendants.height,
    odycrim_defendants.hair_color,
    odycrim_defendants.eye_color,
    odycrim_defendants.case_number
   FROM odycrim_defendants;

REVOKE SELECT ON TABLE public.odytraf_defendants FROM mjcs_ro_redacted;
CREATE OR REPLACE VIEW redacted.odytraf_defendants
 AS
 SELECT odytraf_defendants.id,
    odytraf_defendants.race,
    odytraf_defendants.sex,
    odytraf_defendants.weight,
    odytraf_defendants.city,
    odytraf_defendants.state,
    odytraf_defendants.zip_code,
    odytraf_defendants.height,
    odytraf_defendants.case_number
   FROM odytraf_defendants;