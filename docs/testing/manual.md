# Manual Testing Guide — RAG Business Document Wiki

**Last Updated:** 2026-04-05

## Prerequisites

```bash
# Start all services
docker-compose up -d

# Verify services healthy
docker-compose ps

# Backend URL (default)
BASE="http://localhost:8000/api/v1"

# Swagger UI for interactive testing
# http://localhost:8000/docs
```

## Authentication Setup

All authenticated endpoints require a valid Supabase JWT.

```bash
# Option A: Login via frontend → extract token from browser DevTools
#           Network tab → Authorization header on any API request

# Option B: Use Supabase CLI (local dev)
supabase auth signup --email test@example.com --password testpassword
supabase auth login --email test@example.com --password testpassword

# Set token for all commands below
TOKEN="your-supabase-jwt-here"
```

---

## Endpoint Tests (curl)

### Auth

```bash
# Get current user info
curl -s -H "Authorization: Bearer $TOKEN" $BASE/auth/me | jq
```

### Documents

```bash
# Upload a document
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -F "file=@test-document.pdf" \
  $BASE/documents/upload | jq

# List user's documents
curl -s -H "Authorization: Bearer $TOKEN" $BASE/documents | jq

# Get document by ID
curl -s -H "Authorization: Bearer $TOKEN" $BASE/documents/{doc_id} | jq

# Check processing status
curl -s -H "Authorization: Bearer $TOKEN" $BASE/documents/{doc_id}/status | jq

# Update document visibility
curl -s -X PATCH -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"visibility": "public"}' \
  $BASE/documents/{doc_id}/visibility | jq

# Grant document access
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user-uuid", "permission": "read"}' \
  $BASE/documents/{doc_id}/access | jq

# Revoke document access
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" \
  $BASE/documents/{doc_id}/access/{access_id}

# Delete a document
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" $BASE/documents/{doc_id}
```

### Search

```bash
# Semantic search
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "test search terms"}' \
  $BASE/search | jq

# Get search suggestions
curl -s -H "Authorization: Bearer $TOKEN" "$BASE/search/suggest?q=test"
```

### Chat (RAG)

```bash
# Send a chat message
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "What does this document say about X?"}' \
  $BASE/chat | jq
```

### Organizations

```bash
# List organizations
curl -s -H "Authorization: Bearer $TOKEN" $BASE/organizations | jq

# Get default org
curl -s -H "Authorization: Bearer $TOKEN" $BASE/organizations/default | jq

# Get org quota usage
curl -s -H "Authorization: Bearer $TOKEN" $BASE/organizations/{org_id}/quota | jq

# Get org members
curl -s -H "Authorization: Bearer $TOKEN" $BASE/organizations/{org_id}/members | jq
```

### Groups

```bash
# Create a group
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Group", "description": "Manual test group"}' \
  $BASE/groups | jq

# List groups
curl -s -H "Authorization: Bearer $TOKEN" $BASE/groups | jq

# Add member to group
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user-uuid-here", "role": "member"}' \
  $BASE/groups/{group_id}/members | jq
```

### Admin (requires admin role)

```bash
# List all users
curl -s -H "Authorization: Bearer $TOKEN" $BASE/admin/users | jq

# Update user role
curl -s -X PATCH -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "admin"}' \
  $BASE/admin/users/{user_id} | jq

# Get platform stats
curl -s -H "Authorization: Bearer $TOKEN" $BASE/admin/stats | jq

# Get activity log
curl -s -H "Authorization: Bearer $TOKEN" $BASE/admin/activity | jq
```

---

## Smoke Test Checklist

Quick health check after deployment — run in order:

| # | Test | Expected | Pass? |
|---|------|----------|-------|
| 1 | `GET /docs` | Swagger UI loads | ☐ |
| 2 | `GET /api/v1/auth/me` + token | 200, user info returned | ☐ |
| 3 | `POST /api/v1/documents/upload` + PDF | 201, document created | ☐ |
| 4 | `GET /api/v1/documents` | 200, uploaded doc appears | ☐ |
| 5 | `GET /api/v1/documents/{id}/status` | 200, processing status | ☐ |
| 6 | `POST /api/v1/search` + query | 200, results returned | ☐ |
| 7 | `GET /api/v1/search/suggest?q=test` | 200, suggestions array | ☐ |
| 8 | `POST /api/v1/chat` + message | 200, AI response | ☐ |
| 9 | `GET /api/v1/organizations/default` | 200, org info | ☐ |
| 10 | `GET /api/v1/admin/stats` (admin) | 200, platform stats | ☐ |

---

## Sample Test Files & Q&A

### Setup

```bash
# Generate sample files (PDF, DOCX, XLSX)
python docs/testing/generate-test-files.py

# Files are created in docs/testing/fixtures/
# Upload all three files:
TOKEN="your-supabase-jwt-here"
BASE="http://localhost:8000/api/v1"

curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -F "file=@docs/testing/fixtures/company-policy.pdf" \
  $BASE/documents/upload | jq '.id'  # save as DOC1

curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -F "file=@docs/testing/fixtures/financial-report-q4-2025.docx" \
  $BASE/documents/upload | jq '.id'  # save as DOC2

curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -F "file=@docs/testing/fixtures/product-catalog.xlsx" \
  $BASE/documents/upload | jq '.id'  # save as DOC3

# Wait for processing to complete (check status)
curl -s -H "Authorization: Bearer $TOKEN" $BASE/documents/{doc_id}/status | jq
# Expected: {"status": "completed"}
```

---

### File 1: `company-policy.pdf` — Employee Handbook

**Content:** Remote work policy, leave entitlements, expense reimbursement, code of conduct, performance reviews.

**Key facts to verify:**

| Fact | Value |
|------|-------|
| Max remote days/month | 15 |
| Core remote hours | 10 AM – 3 PM EST |
| Home office stipend | $75/month |
| Annual leave | 20 days/year |
| Sick leave | 12 days/year |
| Expense approval threshold | $500 |
| Max monthly expense (IC) | $2,000 |
| Max monthly expense (manager) | $5,000 |
| Performance review frequency | Quarterly |
| Merit increase range | 2% – 8% |

**Q&A Test Cases:**

```bash
# Q1: Factual — exact number retrieval
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "How many remote work days are allowed per month?"}' \
  $BASE/chat | jq '.answer'
# Expected: mentions "15 days per month"

# Q2: Factual — monetary value
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the home office stipend amount?"}' \
  $BASE/chat | jq '.answer'
# Expected: mentions "$75 per month"

# Q3: Factual — table data
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "How many sick leave days do employees get per year?"}' \
  $BASE/chat | jq '.answer'
# Expected: mentions "12 days"

# Q4: Synthesis — combining multiple facts
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the expense limits for individual contributors vs managers?"}' \
  $BASE/chat | jq '.answer'
# Expected: mentions $2,000 for ICs and $5,000 for managers

# Q5: Conditional logic
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What happens if an employee is rated 1 for two consecutive quarters?"}' \
  $BASE/chat | jq '.answer'
# Expected: mentions "90-day Performance Improvement Plan" or "PIP"

# Q6: Negative — info NOT in document
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the company dress code policy?"}' \
  $BASE/chat | jq '.answer'
# Expected: "couldn't find" or similar — dress code only mentioned as minor violation example, no details

# Q7: Semantic search
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "vacation time off carry over policy"}' \
  $BASE/search | jq '.results[0].content'
# Expected: returns leave policy section mentioning 5-day carry over
```

---

### File 2: `financial-report-q4-2025.docx` — Q4 Financial Report

**Content:** Revenue breakdown, operating expenses, net income, cash position, Q1 2026 outlook.

**Key facts to verify:**

| Fact | Value |
|------|-------|
| Q4 2025 total revenue | $2,400,000 |
| YoY revenue growth | 18% |
| Largest revenue stream | SaaS Subscriptions ($1.2M, 50%) |
| Total expenses | $1,788,000 |
| Net income | $612,000 |
| Net margin | 25.5% |
| Cash position (Dec 31) | $3,800,000 |
| APAC expansion cost | $400,000 |
| New hires planned (Q1 2026) | 15 |

**Q&A Test Cases:**

```bash
# Q1: Factual — top-line number
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What was the total revenue in Q4 2025?"}' \
  $BASE/chat | jq '.answer'
# Expected: mentions "$2,400,000" or "$2.4 million"

# Q2: Factual — from table
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "How much did Professional Services generate in Q4 2025?"}' \
  $BASE/chat | jq '.answer'
# Expected: mentions "$600,000"

# Q3: Comparison / calculation
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What was the year-over-year growth rate and Q4 2024 revenue?"}' \
  $BASE/chat | jq '.answer'
# Expected: mentions 18% growth and $2,034,000

# Q4: Synthesis — from expense table
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What were the top 3 expense categories in Q4 2025?"}' \
  $BASE/chat | jq '.answer'
# Expected: Salaries ($960K), Sales & Marketing ($300K), Cloud ($240K)

# Q5: Forward-looking
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the key initiatives planned for Q1 2026?"}' \
  $BASE/chat | jq '.answer'
# Expected: mentions APAC expansion and AI Assistant product line

# Q6: Specific entity names
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Which new enterprise contracts were signed in November 2025?"}' \
  $BASE/chat | jq '.answer'
# Expected: mentions Globex Inc, Initech, Umbrella Corp

# Q7: Negative — info NOT in document
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What was the Q1 2025 revenue?"}' \
  $BASE/chat | jq '.answer'
# Expected: "couldn't find" — only Q4 data is in the report

# Q8: Semantic search
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "profitability margin earnings"}' \
  $BASE/search | jq '.results[0].content'
# Expected: returns net income section mentioning 25.5% margin
```

---

### File 3: `product-catalog.xlsx` — Product Catalog

**Content:** 3 sheets — Products (10 items), Pricing (3 tiers), Inventory (3 warehouses).

**Key facts to verify:**

| Fact | Value |
|------|-------|
| Total products | 10 |
| Widget Pro price (Tier 1) | $49.99 |
| Most expensive product | Gadget Gamma ($199.99) |
| Cheapest product | Carrying Case XL ($19.99) |
| Total Widget Pro stock | 300 units |
| Critical stock item | Gadget Gamma (20 units) |
| Out of stock item | Carrying Case XL (0 units) |
| Number of warehouses | 3 (NY, LA, CHI) |

**Q&A Test Cases:**

```bash
# Q1: Factual — single product price
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the price of Widget Pro?"}' \
  $BASE/chat | jq '.answer'
# Expected: mentions "$49.99"

# Q2: Factual — from inventory sheet
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "How many Widget Pro units are in stock across all warehouses?"}' \
  $BASE/chat | jq '.answer'
# Expected: mentions "300 units" or "150 + 80 + 70"

# Q3: Comparison across products
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Which products are running low on stock?"}' \
  $BASE/chat | jq '.answer'
# Expected: mentions Widget Max (Low Stock) and Gadget Gamma (Critical)

# Q4: Bulk pricing / tier lookup
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the Tier 3 bulk price for Gadget Alpha when ordering 50 or more?"}' \
  $BASE/chat | jq '.answer'
# Expected: mentions "$103.99"

# Q5: Synthesis — cross-sheet query
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Which products are out of stock and what is their regular price?"}' \
  $BASE/chat | jq '.answer'
# Expected: Carrying Case XL at $19.99

# Q6: Category aggregation
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "How many Widget products are in the catalog?"}' \
  $BASE/chat | jq '.answer'
# Expected: mentions 3 (Widget Pro, Lite, Max)

# Q7: Negative — info NOT in document
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the shipping cost for Widget Pro?"}' \
  $BASE/chat | jq '.answer'
# Expected: "couldn't find" — no shipping info in catalog

# Q8: Semantic search
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "heavy duty industrial equipment load capacity"}' \
  $BASE/search | jq '.results[0].content'
# Expected: returns Widget Max (500kg load capacity)
```

---

### Cross-Document Queries (upload all 3 files first)

```bash
# Q1: Cross-doc factual
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the company expense limit for individuals and what is the most expensive product?"}' \
  $BASE/chat | jq '.answer'
# Expected: mentions $2,000 (expense limit) and Gadget Gamma ($199.99)

# Q2: Cross-doc synthesis
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "How does the Q4 net income compare to total product inventory value?"}' \
  $BASE/chat | jq '.answer'
# Expected: synthesizes financial data with product pricing

# Q3: Disambiguation — "remote" could match multiple docs
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "remote work policy"}' \
  $BASE/search | jq '.results | length'
# Expected: results from company-policy.pdf, not product catalog
```

---

### RAG Quality Verification Checklist

| # | Test | Expected Behavior | Pass? |
|---|------|-------------------|-------|
| 1 | Exact number retrieval | Returns correct numeric value from document | ☐ |
| 2 | Table data extraction | Correctly reads values from tables (leave, pricing, inventory) | ☐ |
| 3 | Multi-hop synthesis | Combines 2+ facts from same document | ☐ |
| 4 | Cross-document query | Retrieves facts from multiple documents | ☐ |
| 5 | Negative case | "Couldn't find" for info not in any uploaded doc | ☐ |
| 6 | Semantic matching | Finds relevant content even with different wording | ☐ |
| 7 | Source citation | `.sources` array contains correct document filenames | ☐ |
| 8 | Processing status | All 3 documents reach "completed" status | ☐ |

---

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| 401 Unauthorized | Expired or missing JWT | Re-login, get fresh token |
| 403 Forbidden | Non-admin accessing admin route | Use admin user token |
| 422 Validation Error | Missing required fields | Check request body schema in Swagger |
| 500 Internal Error | Backend crash | Check `docker-compose logs backend` |
| Connection refused | Backend not running | `docker-compose up -d` |
| MinIO upload fails | MinIO not running | Check port 9000, `docker-compose ps` |
| Document stuck in PROCESSING | Celery worker not running | Check `docker-compose logs celery_worker` |
| Search returns 0 results | Embeddings not generated | Check `GOOGLE_API_KEY` in `.env` |
