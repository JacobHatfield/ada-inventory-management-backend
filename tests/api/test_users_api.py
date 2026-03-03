"""
User management API endpoint tests
- Test GET /api/v1/users/me (get profile)
- Test GET /api/v1/users/me (unauthenticated)
- Test PUT /api/v1/users/me (update profile)
- Test PUT /api/v1/users/me (invalid data)
- Test PUT /api/v1/users/me (unauthenticated)
- Test PATCH /api/v1/users/me/password (change password)
- Test PATCH /api/v1/users/me/password (incorrect old password)
- Test PATCH /api/v1/users/me/password (weak password)
- Test PATCH /api/v1/users/me/password (unauthenticated)
Coverage target: >95%
"""
