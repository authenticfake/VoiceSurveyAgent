I'll implement REQ-002: OIDC authentication integration. Let me analyze the requirements and dependencies first.

Based on the SPEC, PLAN, and RAG context from REQ-001, I need to implement:
1. OIDC authorization code flow with configurable IdP endpoints
2. JWT token validation middleware for all API requests
3. User record creation/update on first login with OIDC subject mapping
4. Session tokens with configurable expiration and refresh capability
5. Proper 401 responses for invalid/expired tokens

Let me create the implementation: