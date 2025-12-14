# PostHog Analytics Integration
# Track server-side events for user behavior analysis

import os

# Initialize PostHog client
posthog_client = None

def get_posthog():
    """Get or initialize PostHog client"""
    global posthog_client
    
    if posthog_client is None:
        api_key = os.environ.get('POSTHOG_API_KEY')
        if api_key:
            import posthog
            posthog.api_key = api_key
            posthog.host = os.environ.get('POSTHOG_HOST', 'https://app.posthog.com')
            posthog_client = posthog
        else:
            # Return a dummy client that does nothing if no API key
            class DummyPostHog:
                def capture(self, *args, **kwargs): pass
                def identify(self, *args, **kwargs): pass
            posthog_client = DummyPostHog()
    
    return posthog_client


def track_event(user, event_name, properties=None):
    """
    Track a server-side event.
    
    Usage:
        track_event(request.user, 'board_created', {'board_id': board.id})
    """
    if properties is None:
        properties = {}
    
    posthog = get_posthog()
    
    # Use user ID as distinct_id (matches frontend identification)
    distinct_id = str(user.id) if hasattr(user, 'id') else 'anonymous'
    
    posthog.capture(
        distinct_id=distinct_id,
        event=event_name,
        properties=properties
    )


def identify_user(user):
    """
    Identify a user with their properties.
    Call this on login/signup.
    
    Usage:
        identify_user(request.user)
    """
    posthog = get_posthog()
    
    posthog.identify(
        distinct_id=str(user.id),
        properties={
            'email': user.email,
            'username': user.username,
            'first_name': getattr(user, 'first_name', ''),
            'last_name': getattr(user, 'last_name', ''),
        }
    )
