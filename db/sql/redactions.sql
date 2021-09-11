-- executed as mjcs_user connected to mjcs database
-- assumes the following role is already created: mjcs_ro_redacted

GRANT SELECT ON ALL TABLES IN SCHEMA public, redacted TO mjcs_ro_redacted;

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

REVOKE SELECT ON TABLE public.dscr_defendant_aliases FROM mjcs_ro_redacted;
CREATE OR REPLACE VIEW redacted.dscr_defendant_aliases
 AS
 SELECT dscr_defendant_aliases.id,
    dscr_defendant_aliases.alias_name,
    dscr_defendant_aliases.city,
    dscr_defendant_aliases.state,
    dscr_defendant_aliases.zip_code
   FROM dscr_defendant_aliases;

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

REVOKE SELECT ON TABLE public.dsk8_defendant_aliases FROM mjcs_ro_redacted;
CREATE OR REPLACE VIEW redacted.dsk8_defendant_aliases
 AS
 SELECT dsk8_defendant_aliases.id,
    dsk8_defendant_aliases.alias_name,
    dsk8_defendant_aliases.city,
    dsk8_defendant_aliases.state,
    dsk8_defendant_aliases.zip_code
   FROM dsk8_defendant_aliases;

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

REVOKE SELECT ON TABLE public.odycvcit_defendants FROM mjcs_ro_redacted;
CREATE OR REPLACE VIEW redacted.odycvcit_defendants
 AS
 SELECT odycvcit_defendants.id,
    odycvcit_defendants.race,
    odycvcit_defendants.sex,
    odycvcit_defendants.weight,
    odycvcit_defendants.city,
    odycvcit_defendants.state,
    odycvcit_defendants.zip_code,
    odycvcit_defendants.height,
    odycvcit_defendants.hair_color,
    odycvcit_defendants.eye_color,
    odycvcit_defendants.case_number
   FROM odycvcit_defendants;

REVOKE SELECT ON TABLE public.dstraf_defendants FROM mjcs_ro_redacted;
CREATE OR REPLACE VIEW redacted.dstraf_defendants
 AS
 SELECT dstraf_defendants.id,
    dstraf_defendants.race,
    dstraf_defendants.sex,
    dstraf_defendants.weight,
    dstraf_defendants.city,
    dstraf_defendants.state,
    dstraf_defendants.zip_code,
    dstraf_defendants.height,
    dstraf_defendants.case_number
   FROM dstraf_defendants;

REVOKE SELECT ON TABLE public.pg_defendants FROM mjcs_ro_redacted;
CREATE OR REPLACE VIEW redacted.pg_defendants
 AS
 SELECT pg_defendants.id,
    pg_defendants.city,
    pg_defendants.state,
    pg_defendants.zip_code,
    pg_defendants.case_number
   FROM pg_defendants;

REVOKE SELECT ON TABLE public.dv_defendants FROM mjcs_ro_redacted;
CREATE OR REPLACE VIEW redacted.dv_defendants
 AS
 SELECT dv_defendants.id,
    dv_defendants.city,
    dv_defendants.state,
    dv_defendants.case_number
   FROM dv_defendants;

COMMIT;