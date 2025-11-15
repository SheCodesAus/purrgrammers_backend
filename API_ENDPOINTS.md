# Purrgrammers Backend API Endpoints

## Overview
This document provides a comprehensive list of all API endpoints for the Purrgrammers retrospective application backend, built with Django REST Framework.

## Base URL
- **Development**: `http://localhost:8000`
- **Production**: `[Your deployed URL]`

---

## Authentication Endpoints

| Method | Endpoint | Description | Request Body | Response | Auth Required |
|--------|----------|-------------|--------------|----------|---------------|
| `POST` | `/api/users/register/` | Register a new user | `{ "username": "string", "email": "string", "first_name": "string", "last_name": "string", "display_name": "string", "password": "string", "password_confirm": "string" }` | `{ "user": {...}, "token": "string", "message": "string" }` | ❌ |
| `POST` | `/api/users/login/` | Login with email or username | `{ "username": "string", "password": "string" }` | `{ "token": "string", "user": {...} }` | ❌ |
| `POST` | `/api/token/` | Alternative token endpoint | `{ "username": "string", "password": "string" }` | `{ "token": "string" }` | ❌ |

---

## Retro Boards Endpoints

| Method | Endpoint | Description | Request Body | Response | Auth Required |
|--------|----------|-------------|--------------|----------|---------------|
| `GET` | `/api/retro-boards/` | List all active retro boards | - | `[{ "id": int, "title": "string", "description": "string", "created_by": {...}, "created_at": "datetime", "updated_at": "datetime", "is_active": boolean }]` | ✅ |
| `POST` | `/api/retro-boards/` | Create a new retro board | `{ "title": "string", "description": "string" }` | `{ "id": int, "title": "string", "description": "string", "created_by": {...}, "created_at": "datetime", "updated_at": "datetime", "is_active": boolean }` | ✅ |
| `GET` | `/api/retro-boards/{id}/` | Get specific retro board details | - | `{ "id": int, "title": "string", "description": "string", "created_by": {...}, "created_at": "datetime", "updated_at": "datetime", "is_active": boolean }` | ✅ |
| `PUT` | `/api/retro-boards/{id}/` | Update a retro board | `{ "title": "string", "description": "string", "is_active": boolean }` | `{ "id": int, "title": "string", "description": "string", "created_by": {...}, "updated_at": "datetime", "is_active": boolean }` | ✅ |
| `DELETE` | `/api/retro-boards/{id}/` | Delete a retro board | - | - | ✅ |
| `GET` | `/api/retro-boards/{id}/columns/` | Get all columns for a specific board | - | `[{ "id": int, "title": "string", "column_type": "string", "position": int, "color": "string", "card_count": int }]` | ✅ |

---

## Columns Endpoints

| Method | Endpoint | Description | Request Body | Response | Auth Required |
|--------|----------|-------------|--------------|----------|---------------|
| `GET` | `/api/columns/` | List all columns | - | `[{ "id": int, "retro_board": int, "title": "string", "column_type": "string", "position": int, "color": "string", "card_count": int }]` | ✅ |
| `POST` | `/api/columns/` | Create a new column | `{ "retro_board": int, "title": "string", "column_type": "string", "position": int, "color": "#hex" }` | `{ "id": int, "retro_board": int, "title": "string", "column_type": "string", "position": int, "color": "string", "card_count": int }` | ✅ |
| `GET` | `/api/columns/{id}/` | Get specific column details | - | `{ "id": int, "retro_board": int, "title": "string", "column_type": "string", "position": int, "color": "string", "card_count": int }` | ✅ |
| `PUT` | `/api/columns/{id}/` | Update a column | `{ "title": "string", "column_type": "string", "position": int, "color": "#hex" }` | `{ "id": int, "retro_board": int, "title": "string", "column_type": "string", "position": int, "color": "string", "card_count": int }` | ✅ |
| `DELETE` | `/api/columns/{id}/` | Delete a column | - | - | ✅ |
| `GET` | `/api/columns/{id}/cards/` | Get all cards for a specific column | - | `[{ "id": int, "content": "string", "created_by": {...}, "position": int, "vote_count": int, "user_has_voted": boolean }]` | ✅ |

---

## Cards Endpoints

| Method | Endpoint | Description | Request Body | Response | Auth Required |
|--------|----------|-------------|--------------|----------|---------------|
| `GET` | `/api/cards/` | List all cards | - | `[{ "id": int, "column": int, "content": "string", "created_by": {...}, "position": int, "is_anonymous": boolean, "vote_count": int, "user_has_voted": boolean }]` | ✅ |
| `POST` | `/api/cards/` | Create a new card | `{ "column": int, "content": "string", "position": int, "is_anonymous": boolean }` | `{ "id": int, "column": int, "content": "string", "created_by": {...}, "position": int, "is_anonymous": boolean, "vote_count": int, "user_has_voted": boolean }` | ✅ |
| `GET` | `/api/cards/{id}/` | Get specific card details | - | `{ "id": int, "column": int, "content": "string", "created_by": {...}, "position": int, "is_anonymous": boolean, "vote_count": int, "user_has_voted": boolean }` | ✅ |
| `PUT` | `/api/cards/{id}/` | Update a card | `{ "content": "string", "position": int, "is_anonymous": boolean }` | `{ "id": int, "column": int, "content": "string", "created_by": {...}, "position": int, "is_anonymous": boolean, "vote_count": int, "user_has_voted": boolean }` | ✅ |
| `DELETE` | `/api/cards/{id}/` | Delete a card | - | - | ✅ |
| `POST` | `/api/cards/{id}/vote/` | Vote on a card | - | `{ "message": "Vote added" }` | ✅ |
| `DELETE` | `/api/cards/{id}/vote/` | Remove vote from a card | - | `{ "message": "Vote removed" }` | ✅ |

---

## Votes Endpoints

| Method | Endpoint | Description | Request Body | Response | Auth Required |
|--------|----------|-------------|--------------|----------|---------------|
| `GET` | `/api/votes/` | List all votes | - | `[{ "id": int, "card": int, "user": {...}, "created_at": "datetime" }]` | ✅ |
| `POST` | `/api/votes/` | Create a new vote | `{ "card": int }` | `{ "id": int, "card": int, "user": {...}, "created_at": "datetime" }` | ✅ |
| `GET` | `/api/votes/{id}/` | Get specific vote details | - | `{ "id": int, "card": int, "user": {...}, "created_at": "datetime" }` | ✅ |
| `PUT` | `/api/votes/{id}/` | Update a vote | `{ "card": int }` | `{ "id": int, "card": int, "user": {...}, "created_at": "datetime" }` | ✅ |
| `DELETE` | `/api/votes/{id}/` | Delete a vote | - | - | ✅ |

---

## Comments Endpoints

| Method | Endpoint | Description | Request Body | Response | Auth Required |
|--------|----------|-------------|--------------|----------|---------------|
| `GET` | `/api/comments/` | List all comments | - | `[{ "id": int, "card": int, "user": {...}, "content": "string", "is_anonymous": boolean, "created_at": "datetime", "updated_at": "datetime" }]` | ✅ |
| `POST` | `/api/comments/` | Create a new comment | `{ "card": int, "content": "string", "is_anonymous": boolean }` | `{ "id": int, "card": int, "user": {...}, "content": "string", "is_anonymous": boolean, "created_at": "datetime", "updated_at": "datetime" }` | ✅ |
| `GET` | `/api/comments/{id}/` | Get specific comment details | - | `{ "id": int, "card": int, "user": {...}, "content": "string", "is_anonymous": boolean, "created_at": "datetime", "updated_at": "datetime" }` | ✅ |
| `PUT` | `/api/comments/{id}/` | Update a comment | `{ "content": "string", "is_anonymous": boolean }` | `{ "id": int, "card": int, "user": {...}, "content": "string", "is_anonymous": boolean, "created_at": "datetime", "updated_at": "datetime" }` | ✅ |
| `DELETE` | `/api/comments/{id}/` | Delete a comment | - | - | ✅ |

---

## Admin Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `GET` | `/admin/` | Django admin interface | ✅ (Admin) |
| `GET` | `/admin/retros/retroboard/` | Manage retro boards | ✅ (Admin) |
| `GET` | `/admin/retros/column/` | Manage columns | ✅ (Admin) |
| `GET` | `/admin/retros/card/` | Manage cards | ✅ (Admin) |
| `GET` | `/admin/retros/vote/` | Manage votes | ✅ (Admin) |
| `GET` | `/admin/retros/comment/` | Manage comments | ✅ (Admin) |
| `GET` | `/admin/users/customuser/` | Manage users | ✅ (Admin) |

---

## Authentication

All API requests (except registration and login) require authentication using Token Authentication.

### Headers
```
Authorization: Token your_token_here
Content-Type: application/json
```

### Column Types Available
- `start` - Start Doing
- `stop` - Stop Doing  
- `keep` - Keep Doing
- `more` - More Of
- `less` - Less Of
- `custom` - Custom

### User Object Structure
```json
{
  "id": 1,
  "username": "string",
  "first_name": "string", 
  "last_name": "string",
  "display_name": "string",
  "initials": "string",
  "created_at": "datetime"
}
```

---

## Error Responses

| Status Code | Description | Example Response |
|-------------|-------------|------------------|
| `400` | Bad Request | `{ "detail": "Invalid data provided" }` |
| `401` | Unauthorized | `{ "detail": "Authentication credentials were not provided" }` |
| `403` | Forbidden | `{ "detail": "You do not have permission to perform this action" }` |
| `404` | Not Found | `{ "detail": "Not found" }` |
| `500` | Server Error | `{ "detail": "Internal server error" }` |

---

## Notes

- All timestamps are in ISO 8601 format
- User IDs are automatically set from the authenticated user
- Cards and columns have position fields for ordering
- Vote system prevents duplicate votes (one vote per user per card)
- Email or username can be used for authentication
- Anonymous posting is supported for cards and comments