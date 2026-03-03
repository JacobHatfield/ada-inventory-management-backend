"""
Category API endpoint tests
- Test POST /api/v1/categories (create)
- Test POST /api/v1/categories (unauthenticated)
- Test POST /api/v1/categories (invalid data)
- Test GET /api/v1/categories (list all)
- Test GET /api/v1/categories (empty list)
- Test GET /api/v1/categories/{category_id} (get single)
- Test GET /api/v1/categories/{category_id} (non-existent)
- Test PUT /api/v1/categories/{category_id} (update)
- Test PUT /api/v1/categories/{category_id} (not owned)
- Test DELETE /api/v1/categories/{category_id}
- Test DELETE /api/v1/categories/{category_id} (with items)
- Test DELETE /api/v1/categories/{category_id} (not owned)
Coverage target: >95%
"""
