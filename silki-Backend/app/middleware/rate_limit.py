from slowapi import Limiter
from slowapi.util import get_remote_address

# Keyed by client IP. Good enough for a single-instance free deployment;
# swap the key_func to pull the user id off the request state once you
# want per-account (rather than per-IP) limits.
limiter = Limiter(key_func=get_remote_address)
