# Inventory Management System - Requirements & Features

## Overview
Enterprise-grade inventory management system following three-layer architecture with Vue 3 + Tailwind CSS frontend, FastAPI middleware, and PostgreSQL database.

---

## 1. User Management Features

### 1.1 Authentication & Authorization
- **User Registration**
  - Create new user accounts
  - Secure password storage (hashing)
  - Email validation
  - Server-side validation

- **User Login**
  - Token-based authentication (JWT)
  - Secure session management
  - Protected routes requiring authentication
  - Clear error handling for auth failures

- **Password Reset** (Higher marks)
  - Email-based password reset workflow
  - Secure token generation
  - Email integration (SendGrid/similar)
  - Complete reset flow from request to new password

- **User Profiles** (Optional - Higher marks)
  - View user profile information
  - Edit profile details
  - Profile image upload (cloud storage integration)

---

## 2. Core Inventory Management Features

### 2.1 Basic CRUD Operations (Essential)
- **Create Inventory Items**
  - Add new items with name, quantity, description
  - Associate items with authenticated user/organization
  - Server-side validation
  - Prevent invalid data entry

- **View Inventory Items**
  - List all inventory items
  - View individual item details
  - Display item attributes clearly

- **Update Inventory Items**
  - Edit item details
  - Update stock quantities
  - Validate changes server-side

- **Delete Inventory Items**
  - Remove items from inventory
  - Confirmation flow
  - Handle related data appropriately

### 2.2 Intermediate Features
- **Stock Level Management**
  - Increment/decrement stock quantities
  - Prevent negative stock values
  - Validation for realistic stock levels

- **Search & Filter**
  - Search items by name
  - Filter by attributes (category, stock level)
  - Sort by various fields

- **Business Logic Implementation**
  - Meaningful validation rules
  - Stock quantity constraints
  - Item attribute requirements

### 2.3 Advanced Features (Higher marks)
- **Low-Stock Alerts**
  - Define threshold levels per item
  - Automatic alerts when stock falls below threshold
  - Email notifications for low stock
  - Visual indicators in UI

- **Item Categorisation**
  - Create and manage categories
  - Assign items to categories
  - Filter by category

- **Audit History**
  - Track all stock changes
  - Record who made changes and when
  - View change history per item
  - Maintain audit trail for compliance

- **Pagination**
  - Server-side pagination for large datasets
  - Performance optimisation
  - Page size configuration

- **Email Notifications**
  - Low-stock alerts
  - System notifications
  - Integration with email service provider

---

## 3. Technical Architecture Requirements

### 3.1 Three-Layer Architecture
```
┌─────────────────────┐
│  Vue 3 + Tailwind   │ (Client-side)
│      Frontend       │
└──────────┬──────────┘
           │ REST API
           │ (JSON)
┌──────────▼──────────┐
│    FastAPI Server   │ (Middleware)
│   - Auth/Authz      │
│   - Business Logic  │
│   - Validation      │
└──────────┬──────────┘
           │ SQLAlchemy ORM
┌──────────▼──────────┐
│     PostgreSQL      │ (Database)
└─────────────────────┘
```

### 3.2 Technology Stack
- **Frontend:** Vue 3 + Vite
- **Styling:** Tailwind CSS
- **Middleware:** FastAPI
- **ORM:** SQLAlchemy
- **Database:** PostgreSQL
- **Authentication:** JWT tokens (python-jose)
- **Email:** SendGrid or similar (optional)
- **Storage:** Cloudinary or similar for media (optional)

### 3.3 Code Organisation
- **Two Separate Repositories:**
  1. Frontend repository (Vue 3 + Tailwind CSS)
  2. Backend/Middleware repository (FastAPI + Database)
- Clean, modular code structure
- Clear separation of concerns
- Independent implementation (not scaffolded)

---

## 4. Security Requirements

### 4.1 Essential Security Features
- **Password Security**
  - Secure password hashing
  - Never store plain text passwords
  - Strong password requirements

- **API Security**
  - Authentication-protected endpoints
  - Token-based authorization
  - Secure token storage and transmission

- **Configuration Security**
  - Environment variables for sensitive data
  - No hardcoded secrets
  - Secure configuration management

- **Error Handling**
  - Clear authentication error messages
  - Authorisation error handling
  - Input validation and sanitisation

---

## 5. Testing Requirements

### 5.1 Required Test Coverage
- **Unit Tests**
  - Test individual functions and methods
  - Test Pydantic models and schemas
  - Test utility functions

- **API Tests**
  - Test all API endpoints
  - Test authentication flows
  - Test CRUD operations
  - Test error scenarios

- **Authentication Tests**
  - Test user registration
  - Test login/logout
  - Test protected routes
  - Test token validation

- **Domain Logic Tests**
  - Test inventory operations
  - Test validation rules
  - Test business logic
  - Test stock management

### 5.2 Testing Strategy
- Clear explanation of what is tested and why
- Tests must run successfully
- Enterprise-quality test practices
- Appropriate test coverage

---

## 6. Deployment Requirements

### 6.1 Basic Deployment
- At least one component (frontend OR backend) deployed
- Accessible via public URL
- Functional and stable

### 6.2 Intermediate Deployment
- Both frontend and backend fully deployed
- Components can communicate
- Environment variables properly configured
- System stable and functional

### 6.3 Advanced Deployment (Highest marks)
- Secure secrets management
- Environment-based configuration
- **CI/CD Pipeline** (GitHub Actions)
  - Automated testing on pull requests
  - Automated linting and formatting checks
  - Automated deployment (optional)
- Deployment must remain active for 3+ weeks after submission
- **Recommended Platform:** Render (free tier)

---

## 7. Documentation Requirements

### 7.1 README Files (Both Repositories)
**Must Include:**
- Application overview
- Setup instructions (step-by-step)
- Usage instructions
- Architecture explanation
- Key technical decisions
- Authentication implementation details
- Deployment configuration and links
- Environment variables documentation
- Testing instructions
- Generative AI usage acknowledgment

**Professional Quality:**
- Clear and concise
- Suitable for enterprise handover
- Well-formatted
- Complete and accurate

### 7.2 API Documentation
- All endpoint descriptions
- Request/response formats
- Authentication requirements
- Error responses
- Example requests

---

## 8. External Integrations (Optional - Higher Marks)

### 8.1 Email Service Integration
- SendGrid or similar email provider
- Use cases:
  - Password reset emails
  - Low-stock alerts
  - System notifications
- Configuration via environment variables
- Error handling for email failures

### 8.2 Cloud Storage Integration
- Cloudinary or similar cloud storage
- Use cases:
  - User profile images
  - Item images
  - File uploads
- Demonstrates scalability
- Separation of concerns

---

## 9. Feature Priority Matrix

### Essential (Must Have) - Required for Pass
- User registration
- User login with JWT authentication
- Protected routes
- Create inventory items
- View inventory items
- Update inventory items
- Delete inventory items
- Basic validation
- User-item association

### Intermediate (Should Have) - Higher Grades
- Stock level updates
- Search and filtering
- Validation to prevent negative stock
- Meaningful business logic
- Both frontend and backend deployed
- Comprehensive testing

### Advanced (Nice to Have) - Highest Grades
- Password reset workflow
- Email notifications
- Low-stock alerts
- Item categorisation
- Audit history
- Pagination
- Editable user profiles
- Cloud storage integration
- CI/CD pipeline

---

## 10. Assessment Criteria

### Grading Breakdown (100% Total)
- **Feature Implementation:** 30%
- **Quality of Architecture:** 30%
- **Testing:** 10%
- **Deployment:** 20%
- **Documentation Quality:** 10%

### Key Principles
- Quality over quantity
- Smaller, well-architected system > larger system with weak separation
- Clear separation of concerns essential
- Enterprise-grade quality expected
- Full understanding of all code required

---

## 11. Development Guidelines

### Do's
- Follow three-layer architecture strictly
- Write clean, modular code
- Implement comprehensive testing
- Document thoroughly
- Use environment variables for configuration
- Acknowledge AI usage in README
- Seek clarification when needed

### Don'ts
- Don't access database directly from frontend
- Don't hardcode secrets or sensitive data
- Don't submit scaffolded/generated code without understanding
- Don't use paid services (free tier only)
- Don't take down deployment before 3 weeks post-submission
- Don't copy code without understanding

---

## 12. Submission Checklist

### Required Deliverables
- [ ] Frontend repository link (Vue 3 + Tailwind CSS)
- [ ] Backend repository link (FastAPI)
- [ ] Video demonstration link (≤20 minutes)
- [ ] Both README files complete
- [ ] Deployment links functional
- [ ] Tests passing
- [ ] Code clean and documented
- [ ] AI usage acknowledged

### Video Demonstration Content
- [ ] User registration demo
- [ ] User login demo
- [ ] Password reset workflow (if implemented)
- [ ] Inventory CRUD operations
- [ ] Validation and business logic
- [ ] Media storage demo (if implemented)
- [ ] Security features explanation
- [ ] Testing demonstration
- [ ] Deployment demonstration
- [ ] Architecture explanation

---

## Support & Resources

- **Supported Stack:** Vue 3, Tailwind CSS, FastAPI, PostgreSQL
- **Deployment Platform:** Render 
