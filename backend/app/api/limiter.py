from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import get_settings

settings = get_settings()

def get_client_key(request):
    """Skip rate limiting for internal endpoints."""
    if request.url.path.startswith("/internal"):
        return "internal"  
    return get_remote_address(request)

limiter = Limiter(
    key_func=get_client_key,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
)

internal_limiter = Limiter(
    key_func=get_client_key,
    default_limits=["10000/minute"], 
)