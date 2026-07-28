# Modèle de données

## Diagramme conceptuel

```mermaid
erDiagram
    USERS ||--o{ INCIDENTS : creates
    USERS o|--o{ INCIDENTS : handles

    USERS ||--o{ INCIDENT_COMMENTS : writes
    INCIDENTS ||--o{ INCIDENT_COMMENTS : contains

    USERS ||--o{ INCIDENT_HISTORY : performs
    INCIDENTS ||--o{ INCIDENT_HISTORY : records

    USERS o|--o{ AUDIT_LOGS : generates

    USERS {
        bigint id PK
        string email UK
        string password_hash
        string full_name
        enum role
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    INCIDENTS {
        bigint id PK
        string reference UK
        string title
        text description
        enum category
        enum priority
        enum status
        bigint created_by_id FK
        bigint assigned_to_id FK
        text resolution
        datetime created_at
        datetime updated_at
        datetime resolved_at
        datetime closed_at
    }

    INCIDENT_COMMENTS {
        bigint id PK
        bigint incident_id FK
        bigint author_id FK
        text content
        datetime created_at
    }

    INCIDENT_HISTORY {
        bigint id PK
        bigint incident_id FK
        bigint actor_id FK
        enum action
        string field_name
        text old_value
        text new_value
        datetime created_at
    }

    AUDIT_LOGS {
        bigint id PK
        bigint user_id FK
        string event_type
        string resource_type
        bigint resource_id
        string result
        string ip_address
        string user_agent
        datetime created_at
    }