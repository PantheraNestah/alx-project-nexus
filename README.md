# PROJECT NEXUS - Movie Recommendation Backend

## A. Core Design and Flowchart Processes

### 1. User Authentication and Management
**Registration**
- Endpoint: `POST /api/auth/register`
- Process: A new user provides credentials (i.e., name, email, password). The backend validates the input, hashes the password, and stores the user in the database.

**Login:**
- Endpoint: `POST /api/auth/login`
- Process: The user submits their credentials. The backend verifies them and, if successful, generates a JSON Web Token (JWT) that is sent back to the client. This token will be used to authenticate subsequent requests.

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
### 1. `users` Table

| Column | Data Type | Constraints / Notes |
| :--- | :--- | :--- |
| `id` | `UUID` / `BIGINT` | Primary Key |
| `name` | `VARCHAR(255)` | `NOT NULL` |
| `email` | `VARCHAR(255)` | `NOT NULL`, `UNIQUE` |
| `password_hash` | `VARCHAR(255)` | `NOT NULL`. **Never store plain text passwords.** |
| `date_of_birth` | `DATE` | `NULLABLE`. Useful for age-gating content. |
| `created_at` | `TIMESTAMP` | Default to `CURRENT_TIMESTAMP` |
| `updated_at` | `TIMESTAMP` | Updates on any row change |


### 2. `genres` Table
TMDb provides a static list of genres with their own IDs.

| Column | Data Type | Constraints / Notes |
| :--- | :--- | :--- |
| `id` | `INTEGER` | Primary Key. **The TMDb genre ID.** |
| `name` | `VARCHAR(255)` | `NOT NULL`, `UNIQUE` |

*   This table is populated once by calling the TMDb `/genre/movie/list` endpoint and storing the results.


### 3. `movies` Table
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


### 4. `movie_genres` (Junction Table)
This table correctly models the many-to-many relationship between movies and genres.

| Column | Data Type | Constraints / Notes |
| :--- | :--- | :--- |
| `movie_id` | `UUID` / `BIGINT` | Foreign Key to `movies.id`. Part of a Composite Primary Key. |
| `genre_id` | `INTEGER` | Foreign Key to `genres.id`. Part of a Composite Primary Key. |


### 5. `user_movie_interactions` Table
A user can have many types of interactions with a movie: liking, bookmarking for later, marking as watched, etc.

| Column | Data Type | Constraints / Notes |
| :--- | :--- | :--- |
| `user_id` | `UUID` / `BIGINT` | Foreign Key to `users.id`. |
| `movie_id` | `UUID` / `BIGINT` | Foreign Key to `movies.id`. |
| `interaction_type`| `VARCHAR(50)` | `NOT NULL`. E.g., 'liked', 'bookmarked', 'watched'. |
| `created_at` | `TIMESTAMP` | Default to `CURRENT_TIMESTAMP`. |

