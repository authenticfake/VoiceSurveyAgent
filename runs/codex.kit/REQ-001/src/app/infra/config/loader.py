import os
from dataclasses import dataclass
from typing import Mapping

from app.auth.errors import OIDCConfigurationError
from app.auth.oidc.config import OIDCConfig


@dataclass(slots=True)
class Settings:
    oidc: OIDCConfig


class ConfigLoader:
    """
    Loads application settings from the environment.

    Future REQs should extend this loader rather than creating new env readers.
    """

    def __init__(self, env: Mapping[str, str] | None = None) -> None:
        self._env = env or os.environ

    def load(self) -> Settings:
        return Settings(oidc=self._load_oidc())

    def _load_oidc(self) -> OIDCConfig:
        required_keys = [
            "OIDC_ISSUER",
            "OIDC_CLIENT_ID",
            "OIDC_CLIENT_SECRET",
            "OIDC_TOKEN_ENDPOINT",
            "OIDC_JWKS_URI",
        ]
        missing = [key for key in required_keys if not self._env.get(key)]
        if missing:
            raise OIDCConfigurationError(f"Missing OIDC settings: {', '.join(missing)}")
        return OIDCConfig(
            issuer=self._env["OIDC_ISSUER"],
            client_id=self._env["OIDC_CLIENT_ID"],
            client_secret=self._env["OIDC_CLIENT_SECRET"],
            token_endpoint=self._env["OIDC_TOKEN_ENDPOINT"],
            jwks_uri=self._env["OIDC_JWKS_URI"],
            audience=self._env.get("OIDC_AUDIENCE"),
        )