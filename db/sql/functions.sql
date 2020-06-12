CREATE OR REPLACE FUNCTION public.age_days(refdate timestamp without time zone)
    RETURNS double precision
    LANGUAGE sql
AS $function$
    SELECT EXTRACT(EPOCH FROM age(refdate))/(60*60*24);
$function$