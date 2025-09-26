# core/utils.py
import requests
from django.conf import settings
from django.core.cache import cache
import logging
from .models import Movie, Genre

logger = logging.getLogger(__name__)

TMDB_API_KEY = settings.TMDB_API_KEY
TMDB_BASE_URL = "https://api.themoviedb.org/3"

def _make_tmdb_request(endpoint, params=None):
    """
    A robust helper function to make requests to the TMDb API.
    Handles common errors and logging.
    """
    if not TMDB_API_KEY:
        logger.critical("TMDB_API_KEY is not configured in settings.py")
        return None

    if params is None:
        params = {}
    params['api_key'] = TMDB_API_KEY
    url = f"{TMDB_BASE_URL}{endpoint}"

    try:
        response = requests.get(url, params=params, timeout=5) # 5-second timeout
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred while calling TMDb {endpoint}: {http_err} - {response.text}")
    except requests.exceptions.ConnectionError as conn_err:
        logger.error(f"Connection error occurred while calling TMDb {endpoint}: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        logger.error(f"Timeout error occurred while calling TMDb {endpoint}: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        logger.error(f"An unexpected error occurred while calling TMDb {endpoint}: {req_err}")
    
    return None

# --- Functions that directly call TMDb ---

def fetch_movie_data_from_tmdb(tmdb_id):
    """Fetches full movie details from TMDb by TMDb ID."""
    data = _make_tmdb_request(f"/movie/{tmdb_id}")
    return data

def get_tmdb_trending_movies():
    """Fetches a list of trending movies from TMDb."""
    data = _make_tmdb_request("/trending/movie/week")
    return data.get('results', []) if data else []

def get_tmdb_movie_details(tmdb_id):
    """Fetches specific movie details from TMDb by TMDb ID."""
    return _make_tmdb_request(f"/movie/{tmdb_id}")

def get_tmdb_movie_recommendations(tmdb_id):
    """Fetches movie recommendations from TMDb for a given TMDb ID."""
    data = _make_tmdb_request(f"/movie/{tmdb_id}/recommendations")
    return data.get('results', []) if data else []


def get_tmdb_movie_search_results(query):
    """Searches for movies on TMDb."""
    data = _make_tmdb_request("/search/movie", params={'query': query})
    return data.get('results', []) if data else []

def save_movie_and_genres_to_db(tmdb_movie_data):
    """
    Upserts movie data into our local database and links genres.
    Returns the Movie object or None if an error occurs.
    """
    if not tmdb_movie_data or not tmdb_movie_data.get('id'):
        logger.warning("Invalid TMDb movie data provided for saving.")
        return None

    tmdb_id = tmdb_movie_data['id']
    try:
        # Use update_or_create for an efficient "upsert" operation.
        # It finds a movie by tmdb_id or creates a new one if it doesn't exist.
        movie, created = Movie.objects.update_or_create(
            tmdb_id=tmdb_id,
            defaults={
                'title': tmdb_movie_data.get('title', 'No Title Provided'),
                'overview': tmdb_movie_data.get('overview', ''),
                'poster_path': tmdb_movie_data.get('poster_path', ''),
                'release_date': tmdb_movie_data.get('release_date') or None, # Handle empty string
                'popularity': tmdb_movie_data.get('popularity', 0.0),
                'vote_average': tmdb_movie_data.get('vote_average', 0.0),
            }
        )

        # TMDb list endpoints provide `genre_ids`, while detail endpoints provide a list of dicts.
        genre_ids_from_tmdb = tmdb_movie_data.get('genre_ids', [])
        if not genre_ids_from_tmdb and tmdb_movie_data.get('genres'):
            genre_ids_from_tmdb = [g['id'] for g in tmdb_movie_data.get('genres', [])]
        
        # Efficiently link genres. This avoids multiple `add()` calls if not necessary.
        if genre_ids_from_tmdb:
            # This will only add genres that are not already linked.
            movie.genres.add(*Genre.objects.filter(id__in=genre_ids_from_tmdb))

        if created:
            logger.info(f"Created new movie in DB: {movie.title} (TMDb ID: {tmdb_id})")
        
        return movie
    except Exception as e:
        logger.error(f"Error saving movie {tmdb_id} to DB: {e}", exc_info=True)
        return None

def seed_initial_genres():
    """
    Fetches the official TMDb genre list and populates our local Genre table.
    This should be run once during initial setup.
    """
    logger.info("Attempting to seed TMDb genres...")
    genres_data = _make_tmdb_request("/genre/movie/list")
    if genres_data and genres_data.get('genres'):
        genres_created_count = 0
        for genre_data in genres_data['genres']:
            obj, created = Genre.objects.update_or_create(
                id=genre_data['id'],
                defaults={'name': genre_data['name']}
            )
            if created:
                genres_created_count += 1
        logger.info(f"TMDb genres seeded successfully. Created {genres_created_count} new genres.")
        return True
    logger.error("Failed to fetch or seed TMDb genres.")
    return False