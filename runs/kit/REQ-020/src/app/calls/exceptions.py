"""
Call-related exceptions for REQ-020.
"""


class CallNotFoundError(Exception):
    """Raised when a call is not found."""
    
    def __init__(self, call_id: str):
        self.call_id = call_id
        super().__init__(f"Call not found: {call_id}")


class CallAccessDeniedError(Exception):
    """Raised when user doesn't have access to the call's campaign."""
    
    def __init__(self, call_id: str, reason: str = "Access denied"):
        self.call_id = call_id
        self.reason = reason
        super().__init__(f"Access denied to call {call_id}: {reason}")