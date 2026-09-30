from .repository import IncidentRepository

def get_incident_repository():
    import config
    return IncidentRepository(config.SUPABASE_URL, config.SUPABASE_SERVICE_ROLE_KEY)
