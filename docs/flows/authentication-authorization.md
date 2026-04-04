# Authentication & Authorization Flow

> Source: [system-architecture.md](../system-architecture.md) - Security Architecture

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend (Vue.js)
    participant Supa as Supabase Auth
    participant API as FastAPI Backend
    participant DB as PostgreSQL

    rect rgb(230, 245, 255)
        Note over User,Supa: REGISTRATION
        User->>FE: Fill registration form
        FE->>FE: Validate email & password
        FE->>Supa: supabase.auth.signUp({email, password})
        Supa->>Supa: Create user in Auth system
        Supa-->>FE: { user, session }
        FE->>API: POST /api/v1/auth/register<br/>Authorization: Bearer {token}
        API->>API: Verify Supabase JWT (JWKS RS256)
        API->>DB: INSERT user profile (role: user)
        DB-->>API: user_id
        API-->>FE: 201 Created
    end

    rect rgb(230, 255, 230)
        Note over User,Supa: LOGIN
        User->>FE: Enter credentials
        FE->>Supa: supabase.auth.signInWithPassword({email, password})
        Supa->>Supa: Verify credentials
        Supa-->>FE: { access_token, refresh_token, user }
        FE->>FE: Store session (Pinia auth store)
    end

    rect rgb(255, 245, 230)
        Note over User,DB: AUTHENTICATED REQUEST
        User->>FE: Perform action
        FE->>API: GET /api/v1/documents<br/>Authorization: Bearer {supabase_token}
        API->>API: Verify JWT via Supabase JWKS (RS256)
        API->>API: Extract user_id from token
        API->>API: Check user role (RBAC)
        API->>DB: Query with user_id filter
        DB-->>API: Results
        API-->>FE: 200 OK + data
    end

    rect rgb(255, 230, 230)
        Note over User,Supa: TOKEN REFRESH
        FE->>Supa: supabase.auth.refreshSession()
        Supa->>Supa: Validate refresh_token
        Supa-->>FE: { access_token, refresh_token }
        FE->>FE: Update session in auth store
    end
```

## RBAC Permission Matrix

```mermaid
graph LR
    subgraph ROLES
        USER["user<br/>(Read-Only)"]
        EDITOR["editor<br/>(Content Manager)"]
        ADMIN["admin<br/>(Full Access)"]
    end

    subgraph PERMS["PERMISSIONS"]
        P1["View Documents"]
        P2["Search Documents"]
        P3["Chat with Documents"]
        P4["Upload Documents"]
        P5["Delete Own Documents"]
        P6["Delete Any Document"]
        P7["Manage Users"]
        P8["View All Documents"]
        P9["View Statistics"]
    end

    USER --> P1
    USER --> P2
    USER --> P3

    EDITOR --> P1
    EDITOR --> P2
    EDITOR --> P3
    EDITOR --> P4
    EDITOR --> P5

    ADMIN --> P1
    ADMIN --> P2
    ADMIN --> P3
    ADMIN --> P4
    ADMIN --> P5
    ADMIN --> P6
    ADMIN --> P7
    ADMIN --> P8
    ADMIN --> P9
```

## Security Details

| Measure | Implementation |
|---------|---------------|
| Authentication | Supabase Auth (managed) |
| Token signing | RS256 via Supabase JWKS |
| Token verification | JWKS public key rotation |
| Token refresh | supabase.auth.refreshSession() |
| Session storage | Pinia auth store |
| CORS | Restricted to allowed origins |
| SQL injection | Parameterized queries via SQLAlchemy |
| Input validation | Pydantic schemas |
