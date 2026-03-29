# Authentication & Authorization Flow

> Source: [system-architecture.md](../system-architecture.md) - Security Architecture

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend (Vue.js)
    participant API as FastAPI Backend
    participant DB as PostgreSQL

    rect rgb(230, 245, 255)
        Note over User,DB: REGISTRATION
        User->>FE: Fill registration form
        FE->>FE: Validate email & password
        FE->>API: POST /api/v1/auth/register<br/>{ email, password }
        API->>API: Check email uniqueness
        API->>API: Hash password (bcrypt, 12 rounds)
        API->>DB: INSERT user (role: 'user')
        DB-->>API: user_id
        API-->>FE: 201 Created
    end

    rect rgb(230, 255, 230)
        Note over User,DB: LOGIN
        User->>FE: Enter credentials
        FE->>API: POST /api/v1/auth/login<br/>{ email, password }
        API->>DB: SELECT user WHERE email = ?
        DB-->>API: user record
        API->>API: Verify bcrypt hash
        API->>API: Generate JWT (HS256, 30min expiry)
        API-->>FE: { access_token, user }
        FE->>FE: Store token in localStorage
    end

    rect rgb(255, 245, 230)
        Note over User,DB: AUTHENTICATED REQUEST
        User->>FE: Perform action
        FE->>API: GET /api/v1/documents<br/>Authorization: Bearer {token}
        API->>API: Decode & verify JWT
        API->>API: Check token expiry
        API->>API: Check user role (RBAC)
        API->>DB: Query with user_id filter
        DB-->>API: Results
        API-->>FE: 200 OK + data
    end

    rect rgb(255, 230, 230)
        Note over User,DB: TOKEN REFRESH
        FE->>API: POST /api/v1/auth/refresh<br/>Authorization: Bearer {old_token}
        API->>API: Verify old token
        API->>API: Generate new JWT
        API-->>FE: { access_token }
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
| Password hashing | bcrypt, 12 salt rounds |
| Token signing | HS256 with JWT_SECRET_KEY |
| Token expiry | 30 minutes |
| Token refresh | POST /auth/refresh |
| CORS | Restricted to allowed origins |
| SQL injection | Parameterized queries via SQLAlchemy |
| Input validation | Pydantic schemas |
