"""
Inventory management routes
- POST /api/v1/inventory - Create new inventory item
- GET /api/v1/inventory - List all items (with search, filter, pagination)
- GET /api/v1/inventory/low-stock - Get low stock items
- GET /api/v1/inventory/{item_id} - Get single item
- GET /api/v1/inventory/{item_id}/history - Get item audit history
- PUT /api/v1/inventory/{item_id} - Update inventory item
- PATCH /api/v1/inventory/{item_id}/stock - Update stock level
- POST /api/v1/inventory/{item_id}/increment - Increment stock
- POST /api/v1/inventory/{item_id}/decrement - Decrement stock
- DELETE /api/v1/inventory/{item_id} - Delete inventory item
"""
