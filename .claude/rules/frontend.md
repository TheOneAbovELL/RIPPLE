---
paths:
  - "apps/web/**"
---
# Frontend rules
- TypeScript strict. API calls through a client generated from the FastAPI OpenAPI schema.
- No business logic in the frontend; it shows what the API returns.
- Memory states use colour AND a text label, never colour alone.
