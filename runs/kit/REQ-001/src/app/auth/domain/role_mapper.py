from typing import Any, Mapping

from app.auth.domain.models import Role


class RoleMapper:
    def map_role(self, claims: Mapping[str, Any]) -> Role:
        raise NotImplementedError


class ConfigurableRoleMapper(RoleMapper):
    """
    Maps roles using configurable claim keys and value mappings.

    Example mapping config:
        {
            "roles": {"admin": Role.admin},
            "groups": {"campaign_managers": Role.campaign_manager},
        }
    """

    def __init__(
        self,
        mapping: Mapping[str, Mapping[str, Role]],
        default_role: Role = Role.viewer,
    ) -> None:
        self._mapping = mapping
        self._default_role = default_role

    def map_role(self, claims: Mapping[str, Any]) -> Role:
        for claim_key, claim_map in self._mapping.items():
            candidate = claims.get(claim_key)
            if candidate is None:
                continue
            values = candidate if isinstance(candidate, list) else [candidate]
            for value in values:
                normalized = str(value).lower()
                if normalized in claim_map:
                    return claim_map[normalized]
        return self._default_role