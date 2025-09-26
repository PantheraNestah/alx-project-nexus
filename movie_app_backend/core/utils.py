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
    """Helper function to make requests to TMDb API."""
    if params is None:
        params = {}
    params['api_key'] = TMDB_API_KEY
    url = f"{TMDB_BASE_URL}{endpoint}"
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
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

def fetch_movie_data_from_tmdb(tmdb_id):
    """Fetches full movie details from TMDb by TMDb ID."""
    data = _make_tmdb_request(f"/movie/{tmdb_id}")
    return data

def get_tmdb_trending_movies():
    """Fetches trending movies from TMDb."""
    data = _make_tmdb_request("/trending/movie/week")
    return data.get('results') if data else []

def get_tmdb_movie_details(tmdb_id):
    """Fetches specific movie details from TMDb by TMDb ID."""
    return _make_tmdb_request(f"/movie/{tmdb_id}")



def get_tmdb_movie_search_results(query):
    """Searches for movies on TMDb."""
    data = _make_tmdb_request("/search/movie", params={'query': query})
    return data.get('results') if data else []

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
        movie, created = Movie.objects.update_or_create(
            tmdb_id=tmdb_id,
            defaults={
                'title': tmdb_movie_data.get('title'),
                'overview': tmdb_movie_data.get('overview'),
                'poster_path': tmdb_movie_data.get('poster_path'),
                'release_date': tmdb_movie_data.get('release_date') if tmdb_movie_data.get('release_date') else None,
                'popularity': tmdb_movie_data.get('popularity', 0.0),
                'vote_average': tmdb_movie_data.get('vote_average', 0.0),
            }
        )

        # Handle genres
        genre_ids_from_tmdb = tmdb_movie_data.get('genre_ids', [])
        if not genre_ids_from_tmdb and tmdb_movie_data.get('genres'): # For detailed movie data, genres is a list of dicts
            genre_ids_from_tmdb = [g['id'] for g in tmdb_movie_data['genres']]

        for genre_id in genre_ids_from_tmdb:
            # Ensure genre exists in our local DB first
            genre_obj, created_genre = Genre.objects.get_or_create(id=genre_id, defaults={'name': f"Genre {genre_id}"})
            # (Optional improvement: fetch actual genre name from TMDb if `created_genre` is True
            # This would require caching TMDb's genre list or a separate call if genre.name is 'Genre X')
            movie.genres.add(genre_obj)
        
        return movie
    except Exception as e:
        logger.error(f"Error saving movie {tmdb_id} to DB: {e}", exc_info=True)
        return None

def seed_initial_genres():
    """Fetches TMDb genres and populates our local Genre table."""
    genres_data = _make_tmdb_request("/genre/movie/list")
    if genres_data and genres_data.get('genres'):
        for genre_data in genres_data['genres']:
            Genre.objects.update_or_create(
                id=genre_data['id'],
                defaults={'name': genre_data['name']}
            )
        logger.info("TMDb genres seeded successfully.")
        return True
    logger.error("Failed to fetch or seed TMDb genres.")
    return False