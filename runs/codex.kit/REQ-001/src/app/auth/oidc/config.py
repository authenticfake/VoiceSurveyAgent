from dataclasses import dataclass


@dataclass(slots=True)
class OIDCConfig:
    issuer: str
    client_id: str
    client_secret: str
    token_endpoint: str
    jwks_uri: str
    audience: str | None = None
    timeout_seconds: int = 15