from django.shortcuts import render
from django.core.cache import cache

from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework_simplejwt.views import TokenObtainPairView

from django.db import IntegrityError
from django.shortcuts import get_object_or_404

from .models import User, Movie, Genre, UserMovieInteraction, Role
from .serializers import (
    UserRegisterSerializer, UserProfileSerializer, MovieSerializer,
    UserMovieInteractionSerializer, AdminUserSerializer, AssignRoleSerializer
)
from .permissions import IsAdminOrReadOnly, IsAdminUser
from .utils import (
    fetch_movie_data_from_tmdb, save_movie_and_genres_to_db,
    get_tmdb_trending_movies, get_tmdb_movie_details, get_tmdb_movie_recommendations,
    get_tmdb_movie_search_results
)

import logging
logger = logging.getLogger(__name__)

# --- Common Response Helpers ---
def success_response(data, message="Operation successful", status_code=status.HTTP_200_OK):
    return Response({
        "status": "success",
        "message": message,
        "data": data
    }, status=status_code)

def error_response(message, code="GENERIC_ERROR", status_code=status.HTTP_400_BAD_REQUEST, details=None):
    return Response({
        "status": "error",
        "message": message,
        "code": code,
        "details": details
    }, status=status_code)

# --- Authentication & User Management ---

class CustomTokenObtainPairView(TokenObtainPairView):
    # This view is provided by simplejwt, but you can customize it if needed
    pass

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    serializer = UserRegisterSerializer(data=request.data)
    if serializer.is_valid():
        try:
            user = serializer.save()
            # Optionally log in user immediately and return tokens
            # For simplicity, we just return success for now
            return success_response(
                {"username": user.username, "email": user.email},
                message="User registered successfully. Please log in.",
                status_code=status.HTTP_201_CREATED
            )
        except IntegrityError:
            return error_response(
                "User with this email or username already exists.",
                code="DUPLICATE_USER",
                status_code=status.HTTP_409_CONFLICT
            )
    return error_response(
        "Registration failed due to invalid data.",
        code="VALIDATION_ERROR",
        status_code=status.HTTP_400_BAD_REQUEST,
        details=serializer.errors
    )

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return success_response(serializer.data)

    def put(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return success_response(serializer.data, message="Profile updated successfully.")
        return error_response(
            "Profile update failed.",
            code="VALIDATION_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=serializer.errors
        )

# --- Movie Data ---

class TrendingMoviesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cache_key = 'trending_movies'
        cached_data = cache.get(cache_key)

        if cached_data:
            logger.info("Serving trending movies from cache.")
            return success_response(cached_data)
        
        logger.info("Cache miss for trending movies. Fetching from TMDb.")

        try:
            tmdb_movies_data = get_tmdb_trending_movies()
            if not tmdb_movies_data:
                return error_response(
                    "Could not fetch trending movies.", 
                    code="TMDB_API_ERROR", 
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE
                )

            local_movies = []
            for tmdb_movie in tmdb_movies_data:
                movie_obj = save_movie_and_genres_to_db(tmdb_movie)
                if movie_obj:
                    local_movies.append(movie_obj)

            serializer = MovieSerializer(local_movies, many=True)
            
            # Cache the result for 1 hour (3600 seconds)
            cache.set(cache_key, serializer.data, timeout=3600)
            
            return success_response(serializer.data)
        except Exception as e:
            logger.error(f"Error fetching trending movies: {e}", exc_info=True)
            return error_response(
                "An unexpected error occurred.", 
                code="SERVER_ERROR", 
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class MovieDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, movie_id): # movie_id here is our internal UUID
        try:
            movie = get_object_or_404(Movie, id=movie_id)
            serializer = MovieSerializer(movie)
            return success_response(serializer.data)
        except Movie.DoesNotExist:
            return error_response("Movie not found.", code="MOVIE_NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error fetching movie detail for {movie_id}: {e}")
            return error_response(
                "An unexpected error occurred while fetching movie details.",
                code="SERVER_ERROR",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# --- MovieDetailByTmdbIdView with Caching ---
class MovieDetailByTmdbIdView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, tmdb_id):
        cache_key = f'movie_detail_{tmdb_id}'
        cached_data = cache.get(cache_key)

        if cached_data:
            logger.info(f"Serving movie detail for TMDb ID {tmdb_id} from cache.")
            return success_response(cached_data)
        
        # If not in cache, check our local DB first. This is faster than an API call.
        try:
            movie = Movie.objects.get(tmdb_id=tmdb_id)
            serializer = MovieSerializer(movie)
            cache.set(cache_key, serializer.data, timeout=86400) # Cache for 24 hours
            logger.info(f"Serving movie detail for TMDb ID {tmdb_id} from DB and caching it.")
            return success_response(serializer.data)
        except Movie.DoesNotExist:
            logger.info(f"Movie with TMDb ID {tmdb_id} not in DB. Fetching from TMDb.")
            pass # Not in local DB, proceed to TMDb API call

        try:
            tmdb_movie_data = get_tmdb_movie_details(tmdb_id)
            if not tmdb_movie_data:
                return error_response(
                    f"Movie with TMDb ID {tmdb_id} not found.", code="TMDB_MOVIE_NOT_FOUND", 
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            movie_obj = save_movie_and_genres_to_db(tmdb_movie_data)
            serializer = MovieSerializer(movie_obj)
            
            cache.set(cache_key, serializer.data, timeout=86400) # Cache for 24 hours
            return success_response(serializer.data)
        except Exception as e:
            logger.error(f"Error fetching movie detail for TMDb ID {tmdb_id}: {e}", exc_info=True)
            return error_response(
                "An unexpected error occurred.", 
                code="SERVER_ERROR", 
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class MovieRecommendationsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, movie_id): # This movie_id is our internal UUID
        try:
            base_movie = get_object_or_404(Movie, id=movie_id)
            # Use base_movie.tmdb_id to call TMDb recommendations API
            tmdb_recommendations_data = get_tmdb_movie_recommendations(base_movie.tmdb_id)

            if not tmdb_recommendations_data:
                return success_response([], message="No recommendations found for this movie.")

            local_recommendations = []
            for tmdb_rec in tmdb_recommendations_data:
                movie_obj = save_movie_and_genres_to_db(tmdb_rec) # Upsert into local DB
                if movie_obj:
                    local_recommendations.append(movie_obj)

            serializer = MovieSerializer(local_recommendations, many=True)
            return success_response(serializer.data)

        except Movie.DoesNotExist:
            return error_response("Base movie for recommendations not found.", code="MOVIE_NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error fetching recommendations for movie {movie_id}: {e}")
            return error_response(
                "An unexpected error occurred while fetching recommendations.",
                code="SERVER_ERROR",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MovieSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get('query', '').strip()
        if not query:
            return error_response("Search query parameter is required.", code="MISSING_QUERY", status_code=status.HTTP_400_BAD_REQUEST)

        try:
            # 1. Check cache for search results (short TTL)
            # 2. If cache miss, call TMDb API for search
            tmdb_search_results = get_tmdb_movie_search_results(query)

            if not tmdb_search_results:
                return success_response([], message="No movies found for your query.")

            local_movies = []
            for tmdb_movie in tmdb_search_results:
                movie_obj = save_movie_and_genres_to_db(tmdb_movie) # Upsert into local DB
                if movie_obj:
                    local_movies.append(movie_obj)

            serializer = MovieSerializer(local_movies, many=True)
            # 3. Cache the serialized data for future requests (short TTL)
            return success_response(serializer.data)

        except Exception as e:
            logger.error(f"Error during movie search for query '{query}': {e}")
            return error_response(
                "An unexpected error occurred during movie search.",
                code="SERVER_ERROR",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserRecommendationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # --- Recommendation Logic Here ---
        # 1. Fetch user's `UserMovieInteraction`s (liked movies, watched genres, etc.)
        # 2. Use this data to query your local `Movie` database.
        #    e.g., Get movies from genres liked by the user, exclude already interacted movies.
        #    For a simple start: find genres from liked movies, then recommend other movies from those genres.

        liked_movies = request.user.interactions.filter(interaction_type=UserMovieInteraction.InteractionType.LIKED)
        liked_genres_ids = set()
        for interaction in liked_movies:
            for genre in interaction.movie.genres.all():
                liked_genres_ids.add(genre.id)

        if not liked_genres_ids:
            # Fallback: if user has no liked movies, recommend trending
            return success_response(TrendingMoviesView().get(request).data, message="No specific preferences yet, showing trending movies.")


        # Get movies that belong to liked genres, excluding movies the user has already interacted with
        interacted_movie_ids = request.user.interactions.values_list('movie__id', flat=True)
        recommended_movies = Movie.objects.filter(
            genres__id__in=list(liked_genres_ids)
        ).exclude(
            id__in=list(interacted_movie_ids)
        ).distinct().order_by('-popularity')[:20] # Limit to top 20, sort by popularity

        serializer = MovieSerializer(recommended_movies, many=True)
        return success_response(serializer.data, message="Personalized recommendations generated.")

# --- User Interactions ---

class UserInteractionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        interactions = request.user.interactions.all() # Fetch all interactions for the user
        serializer = UserMovieInteractionSerializer(interactions, many=True)
        return success_response(serializer.data)

    def post(self, request):
        # The frontend should send our internal movie UUID.
        # This is more secure and efficient.
        request_data = request.data.copy()
        request_data['user'] = request.user.id # Add user to data for serializer
        
        serializer = UserMovieInteractionSerializer(data=request_data)
        if serializer.is_valid():
            try:
                serializer.save(user=request.user) # Pass user object directly to save method
                return success_response(serializer.data, message="Interaction saved.", status_code=status.HTTP_201_CREATED)
            except IntegrityError:
                return error_response("This interaction already exists.", code="DUPLICATE_INTERACTION", status_code=status.HTTP_409_CONFLICT)
        
        return error_response("Invalid data provided.", code="VALIDATION_ERROR", details=serializer.errors)


class UserInteractionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, interaction_id):
        # Ensure the interaction belongs to the authenticated user
        interaction = get_object_or_404(UserMovieInteraction, id=interaction_id, user=request.user)
        interaction.delete()
        return success_response(None, message="Interaction deleted successfully.", status_code=status.HTTP_204_NO_CONTENT)


# --- Admin Endpoints ---

# We need a custom permission for admin users
from rest_framework.permissions import BasePermission

class IsAdminUser(BasePermission):
    """
    Allows access only to admin users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser) # Using is_superuser for simplicity for now. For roles, we'd check user.roles.filter(name='admin').exists()

class AdminUserListView(APIView):
    permission_classes = [IsAdminUser] # Ensure only admins can access

    def get(self, request):
        users = User.objects.all().order_by('username')
        serializer = AdminUserSerializer(users, many=True)
        return success_response(serializer.data)

class AdminUserDetailView(APIView):
    permission_classes = [IsAdminUser]

    def delete(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        if user == request.user:
            return error_response("You cannot delete your own admin account.", code="SELF_DELETE_FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN)
        user.delete()
        return success_response(None, message="User deleted successfully.", status_code=status.HTTP_204_NO_CONTENT)

class AdminRoleAssignmentView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = AssignRoleSerializer(data=request.data)
        if serializer.is_valid():
            user_id = serializer.validated_data['user_id']
            role_name = serializer.validated_data['role_name']

            try:
                user = User.objects.get(id=user_id)
                role, created = Role.objects.get_or_create(name=role_name) # Ensure role exists
                user.roles.add(role)
                return success_response(
                    {"user": user.username, "role": role.name},
                    message=f"Role '{role.name}' assigned to user '{user.username}' successfully.",
                    status_code=status.HTTP_200_OK
                )
            except User.DoesNotExist:
                return error_response("User not found.", code="USER_NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                logger.error(f"Error assigning role: {e}")
                return error_response(
                    "An unexpected error occurred while assigning role.",
                    code="SERVER_ERROR",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return error_response(
            "Invalid role assignment data.",
            code="VALIDATION_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=serializer.errors
        )