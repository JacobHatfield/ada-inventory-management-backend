"""
Rate limiting API tests
- Test POST /api/v1/auth/login rate limit (10 req/min)
- Test POST /api/v1/auth/register rate limit (5 req/min)
- Test rate limit headers in response
- Test rate limit reset after time period
- Test rate limit applies per IP address
- Test rate limit exceeded error (429 status)
- Test rate limit error message format
- Test different endpoints have different limits
Coverage target: >95%
"""
