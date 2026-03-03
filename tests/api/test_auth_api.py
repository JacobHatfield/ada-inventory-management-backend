"""
Authentication API endpoint tests
- Test POST /api/v1/auth/register (success)
- Test POST /api/v1/auth/register (validation errors)
- Test POST /api/v1/auth/register (duplicate email)
- Test POST /api/v1/auth/login (valid credentials)
- Test POST /api/v1/auth/login (invalid credentials)
- Test POST /api/v1/auth/login (non-existent user)
- Test GET /api/v1/auth/me (authenticated)
- Test GET /api/v1/auth/me (unauthenticated)
- Test GET /api/v1/auth/me (expired token)
- Test GET /api/v1/auth/me (invalid token)
- Test POST /api/v1/auth/forgot-password
- Test POST /api/v1/auth/reset-password
- Test password reset token expiration
Coverage target: >95%
"""
