# PROJECT NEXUS - Movie Recommendation Backend

## Table of Contents
1. [Core Design and Processes](#a-core-design-and-flowchart-processes)
   - User Authentication and Management
   - TMDb API Integration
   - User Preferences
   - Robust Error Handling
2. [Schema Design](#b-schema-design)
3. [API Endpoint Design and Responsibilities](#c-api-endpoint-design-and-responsibilities)
4. [Project Setup Instructions](#d-project-setup-instructions)

## A. Core Design and Processes

### 1. User Authentication and Management
**Registration**
- Endpoint: `POST /api/auth/register`
- Process: A new user provides credentials (i.e., name, email, password). The backend validates the input, hashes the password, and stores the user in the database.

**Login:**
- Endpoint: `POST /api/auth/login`
- Process: The user submits their credentials. The backend verifies them and, if successful, generates a JSON Web Token (JWT) that is sent back to the client. This token will be used to authenticate subsequent requests.

**The RBAC Strategy**

1.  **`roles` Table**: A simple table to define the roles available in the system (i.e., "user", "admin", "moderator").
2.  **`user_roles` Table**: A junction table that links a user to one or more roles. This is powerful because a user can potentially have multiple roles if needed in the future.

This design is good practice and scalable because it allows to easily add more roles later (like `ContentManager`) without changing the database schema.

**User Profile**
- Endpoint: `GET /api/user/profile`
- Process: The authenticated user can view their profile information and saved preferences.

### 2. TMDb API Integration and Data Fetching
This process handles all interactions with the third-party TMDb API. It's crucial to isolate this logic to handle errors and potential API changes gracefully.

**Fetching Trending Movies:**
- Endpoint: `GET /api/movies/trending`
- Process: The backend calls the TMDb API's trending endpoint. The results are then processed and sent to the client. This is a prime candidate for caching.

**Movie Details:**
- Endpoint: `GET /api/movies/{tmdb_movie_id}`
- Process: When a user wants to see more details about a movie, the backend fetches this information from TMDb using the movie's ID. This data is also highly cacheable.

**Movie Recommendations:**
- Endpoint: GET /api/movies/{tmdb_movie_id}/recommendations
- Process: Your backend can leverage TMDb's "recommendations" or "similar movies" endpoint to get a list of related movies.

### 3. User Preferences and Personalized Recommendations
The core of the user-centric design, making the recommendations relevant to each user.

**Saving Preferences:**
- Endpoint: `POST /api/user/preferences`
- Process: Authenticated users can save their favorite genres, actors, or specific movies they liked. This data is stored in our database against their user profile.

**Personalized Recommendations Endpoint:**
- Endpoint: GET /api/user/recommendations
- Process: This is where the magic happens. The backend can use a combination of the user's saved preferences and their viewing history to generate a personalized list of movies. For a start, we can fetch movies from TMDb that match the user's favorite genres.

### 4. Robust Error Handling
- API Call Failures: Implementing try-catch blocks for all calls to the TMDb API.
- Fallback Mechanisms: If a call to TMDb fails, the backend can serve data from the cache or return a user-friendly error message.
- Consistent Error Responses: Using a standard error response format for the API so the frontend can handle errors consistently. For example:
``` 
{
  "status": "error",
  "message": "Could not fetch trending movies at this time. Please try again later."
} 
```

## B. Schema Design
### Database Models

### 1. `roles` Table (New)
This table will store the distinct roles. You will likely "seed" this table with initial data when you first set up the database.

| Column | Data Type | Constraints / Notes |
| :--- | :--- | :--- |
| `id` | `INTEGER` | Primary Key |
| `name` | `VARCHAR(50)` | `NOT NULL`, `UNIQUE`. (e.g., 'user', 'admin') |


### 2. `user_roles` Table (New)
This is the junction table that assigns roles to users.

| Column | Data Type | Constraints / Notes |
| :--- | :--- | :--- |
| `user_id` | `UUID` / `BIGINT` | Foreign Key to `users.id`. Part of a Composite Primary Key. |
| `role_id` | `INTEGER` | Foreign Key to `roles.id`. Part of a Composite Primary Key. |


### 3. `users` Table

| Column | Data Type | Constraints / Notes |
| :--- | :--- | :--- |
| `id` | `UUID` / `BIGINT` | Primary Key |
| `name` | `VARCHAR(255)` | `NOT NULL` |
| `email` | `VARCHAR(255)` | `NOT NULL`, `UNIQUE` |
| `password_hash` | `VARCHAR(255)` | `NOT NULL`. **Never store plain text passwords.** |
| `date_of_birth` | `DATE` | `NULLABLE`. Useful for age-gating content. |
| `created_at` | `TIMESTAMP` | Default to `CURRENT_TIMESTAMP` |
| `updated_at` | `TIMESTAMP` | Updates on any row change |


### 4. `genres` Table
TMDb provides a static list of genres with their own IDs.

| Column | Data Type | Constraints / Notes |
| :--- | :--- | :--- |
| `id` | `INTEGER` | Primary Key. **The TMDb genre ID.** |
| `name` | `VARCHAR(255)` | `NOT NULL`, `UNIQUE` |

*   This table is populated once by calling the TMDb `/genre/movie/list` endpoint and storing the results.


### 5. `movies` Table
This is the local mirror of essential movie data from TMDb. It enforces that each movie from TMDb is stored only once.

| Column | Data Type | Constraints / Notes |
| :--- | :--- | :--- |
| `id` | `UUID` / `BIGINT` | Primary Key (Internal to our system). |
| `tmdb_id` | `INTEGER` | `NOT NULL`, `UNIQUE`. **Crucial for preventing duplicates.** |
| `title` | `VARCHAR(255)` | `NOT NULL` |
| `overview` | `TEXT` | |
| `poster_path` | `VARCHAR(255)`| |
| `release_date` | `DATE` | |
| `popularity` | `FLOAT` | From TMDb. Great for sorting trending movies. |
| `vote_average` | `FLOAT` | From TMDb. |
| `created_at` | `TIMESTAMP` | Default to `CURRENT_TIMESTAMP` |
| `updated_at` | `TIMESTAMP` | When we last synced this row with TMDb. |

*   **A `UNIQUE` constraint on `tmdb_id` is critical for performance and data integrity.** This prevents the same movie from being inserted multiple times.
*   The `popularity` and `vote_average` fields, will be very useful for building recommendation logic without calling the API again.
*   The `updated_at` field can help build a mechanism to periodically refresh movie data from TMDb if needed.


### 6. `movie_genres` (Junction Table)
This table correctly models the many-to-many relationship between movies and genres.

| Column | Data Type | Constraints / Notes |
| :--- | :--- | :--- |
| `movie_id` | `UUID` / `BIGINT` | Foreign Key to `movies.id`. Part of a Composite Primary Key. |
| `genre_id` | `INTEGER` | Foreign Key to `genres.id`. Part of a Composite Primary Key. |


### 7. `user_movie_interactions` Table
A user can have many types of interactions with a movie: liking, bookmarking for later, marking as watched, etc.

| Column | Data Type | Constraints / Notes |
| :--- | :--- | :--- |
| `user_id` | `UUID` / `BIGINT` | Foreign Key to `users.id`. |
| `movie_id` | `UUID` / `BIGINT` | Foreign Key to `movies.id`. |
| `interaction_type`| `VARCHAR(50)` | `NOT NULL`. E.g., 'liked', 'bookmarked', 'watched'. |
| `created_at` | `TIMESTAMP` | Default to `CURRENT_TIMESTAMP`. |


---

## D. Project Setup Instructions

Follow these steps to set up and run the project:

### 1. Prerequisites
Ensure you have the following installed:
- Python 3.11+
- pip
- Virtualenv (`python3 -m venv venv`)
- PostgreSQL (optional if using Docker)
- Git

### 2. Clone the Repository
```bash
git clone https://github.com/PantheraNestah/alx-project-nexus.git
cd alx-project-nexus
cd movie_app_backend
```

### 3. Setup Environment and Variables

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Database Setup

### 6. Seed Movie Genres Data
```bash
python manage.py seed_genres
```

### 7. Run The Project
Start the development server:
```bash
python manage.py runserver
```
Or with Docker:
```bash
docker-compose up --build
```
Visit: http://127.0.0.1:8000

## C. API Endpoint Design and Responsibilities

Categorizing endpoints by their primary resource.

#### **Authentication & User Management (`/api/auth`, `/api/user`)**

*   **`POST /api/auth/register`**
    *   **Responsibility**: Register a new user, hash password, assign default 'user' role, generate JWT.
*   **`POST /api/auth/login`**
    *   **Responsibility**: Authenticate user credentials, generate JWT upon success.
*   **`GET /api/user/profile`**
    *   **Responsibility**: Retrieve the authenticated user's profile details.
    *   **Authentication**: JWT required.
*   **`PUT /api/user/profile`**
    *   **Responsibility**: Update the authenticated user's profile details (e.g., `date_of_birth`).
    *   **Authentication**: JWT required.

#### **Movie Data (`/api/movies`)**

*   **`GET /api/movies/trending`**
    *   **Responsibility**: Fetch and serve a list of trending movies. This is a primary candidate for *caching* and will involve interaction with TMDb API if cache is cold.
*   **`GET /api/movies/{movie_id}`**
    *   **Responsibility**: Retrieve detailed information for a specific movie. Also a strong *caching* candidate.
*   **`GET /api/movies/{movie_id}/recommendations`**
    *   **Responsibility**: Fetch and serve a list of recommended movies based on the given `movie_id` (using TMDb's similar/recommendations endpoint).
*   **`GET /api/movies/search?query={term}`**
    *   **Responsibility**: Search for movies by title. Will hit TMDb API, results can be cached short-term.

#### **User Preferences & Interactions (`/api/user/interactions`, `/api/user/recommendations`)**

*   **`GET /api/user/interactions`**
    *   **Responsibility**: Retrieve all interactions (liked, bookmarked) for the authenticated user.
    *   **Authentication**: JWT required.
*   **`POST /api/user/interactions`**
    *   **Responsibility**: Record a new interaction (like/bookmark) for an authenticated user with a specific movie. This will involve:
        1.  Checking if the movie exists in the DB (by `tmdb_id`).
        2.  If not, fetch details from TMDb and save to the `Movie` table and `MovieGenre` table.
        3.  Create the `UserMovieInteraction` record.
    *   **Authentication**: JWT required.
*   **`DELETE /api/user/interactions/{interaction_id}`**
    *   **Responsibility**: Remove a specific user interaction.
    *   **Authentication**: JWT required.
*   **`GET /api/user/recommendations`**
    *   **Responsibility**: Generate and serve personalized movie recommendations for the authenticated user based on their saved preferences and interactions. This is where the custom recommendation logic will live, possibly leveraging cached data or simple preference matching.
    *   **Authentication**: JWT required.

#### **Admin Endpoints (`/api/admin`) - (Requires 'admin' role)**

*   **`GET /api/admin/users`**
    *   **Responsibility**: Retrieve a list of all users.
    *   **Authentication**: JWT with 'admin' role.
*   **`DELETE /api/admin/users/{user_id}`**
    *   **Responsibility**: Delete a specific user.
    *   **Authentication**: JWT with 'admin' role.
*   **`POST /api/admin/roles/assign`**
    *   **Responsibility**: Assign a specific role to a user.
    *   **Authentication**: JWT with 'admin' role.

---

## D. Request/Response Structure & Error Handling

#### **Standard Success Response Structure**

```json
{
  "status": "success",
  "message": "Operation successful",
  "data": {
    // Actual data specific to the endpoint
  }
}
```

#### **Standard Error Response Structure**

```json
{
  "status": "error",
  "message": "A descriptive error message.",
  "code": "A_UNIQUE_ERROR_CODE",
  "details": {}
}
```

**Common Error Codes/Statuses:**
*   `400 Bad Request`: Invalid input (e.g., missing fields, wrong format).
*   `401 Unauthorized`: No authentication token provided or token is invalid/expired.
*   `403 Forbidden`: Authentication token provided, but user does not have necessary permissions (e.g., not an admin).
*   `404 Not Found`: Resource not found.
*   `409 Conflict`: Resource already exists (e.g., registering with an existing email).
*   `500 Internal Server Error`: Something went wrong on the backend.
*   `503 Service Unavailable`: External service (TMDb) is unreachable or returned an error.

---

