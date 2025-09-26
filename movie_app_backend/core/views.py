from django.shortcuts import render

# Create your views here.

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
from .permissions import IsAdminOrReadOnly
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
    permission_classes = [AllowAny] # Can be restricted later if needed

    def get(self, request):
        try:
            # --- Caching Logic Here ---
            # 1. Check if trending movies are in cache (e.g., Redis)
            #    If yes, return cached data.
            # 2. If no (cache miss), call TMDb API via utils function
            tmdb_movies_data = get_tmdb_trending_movies() # This function handles error internally
            if not tmdb_movies_data:
                return error_response(
                    "Could not fetch trending movies from TMDb.",
                    code="TMDB_API_ERROR",
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE
                )

            # 3. For each movie from TMDb, upsert into our local DB
            #    This is where `save_movie_and_genres_to_db` from utils comes in.
            local_movies = []
            for tmdb_movie in tmdb_movies_data:
                movie_obj = save_movie_and_genres_to_db(tmdb_movie)
                if movie_obj:
                    local_movies.append(movie_obj)

            serializer = MovieSerializer(local_movies, many=True)
            # 4. Cache the serialized data for future requests (with a TTL)
            #    e.g., cache.set('trending_movies', serializer.data, timeout=3600)
            return success_response(serializer.data)

        except Exception as e:
            logger.error(f"Error fetching trending movies: {e}")
            return error_response(
                "An unexpected error occurred while fetching trending movies.",
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

# Placeholder for specific TMDb ID details
class MovieDetailByTmdbIdView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, tmdb_id):
        # 1. Check cache for tmdb_id (e.g., Redis)
        # 2. Check local DB for tmdb_id
        try:
            movie = Movie.objects.get(tmdb_id=tmdb_id)
            serializer = MovieSerializer(movie)
            # If found in DB, cache it for later if not already
            return success_response(serializer.data)
        except Movie.DoesNotExist:
            pass # Not in local DB, proceed to TMDb

        # 3. If not in local DB, fetch from TMDb
        try:
            tmdb_movie_data = get_tmdb_movie_details(tmdb_id)
            if not tmdb_movie_data:
                return error_response(
                    f"Movie with TMDb ID {tmdb_id} not found or TMDb API error.",
                    code="TMDB_MOVIE_NOT_FOUND",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            movie_obj = save_movie_and_genres_to_db(tmdb_movie_data) # Save to local DB
            serializer = MovieSerializer(movie_obj)
            # Cache the result
            return success_response(serializer.data)

        except Exception as e:
            logger.error(f"Error fetching movie detail for TMDb ID {tmdb_id}: {e}")
            return error_response(
                "An unexpected error occurred while fetching movie details.",
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


# --- User Interactions ---

class UserInteractionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        interactions = request.user.interactions.all() # Fetch all interactions for the user
        serializer = UserMovieInteractionSerializer(interactions, many=True)
        return success_response(serializer.data)

    def post(self, request):
        serializer = UserMovieInteractionSerializer(data=request.data)
        if serializer.is_valid():
            tmdb_movie_id = serializer.validated_data['movie'].tmdb_id # Get tmdb_id from validated movie object

            # Ensure movie exists in our DB. If not, fetch from TMDb and save.
            try:
                movie_obj = Movie.objects.get(tmdb_id=tmdb_movie_id)
            except Movie.DoesNotExist:
                # This should ideally be handled by frontend sending our internal movie ID
                # or the serializer validating it. For now, assume movie exists or TMDB ID is sent.
                # If frontend sends internal UUID, then we just need to get Movie object
                movie_uuid = request.data.get('movie')
                if not movie_uuid:
                     return error_response("Movie ID is required for interaction.", code="INVALID_INPUT", status_code=status.HTTP_400_BAD_REQUEST)
                try:
                    movie_obj = Movie.objects.get(id=movie_uuid)
                except Movie.DoesNotExist:
                     return error_response("Movie not found in our database.", code="MOVIE_NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND)


            try:
                serializer.save(user=request.user, movie=movie_obj) # Set user and movie from context
                return success_response(serializer.data, message="Interaction saved successfully.", status_code=status.HTTP_201_CREATED)
            except IntegrityError:
                return error_response(
                    "You have already recorded this interaction for this movie.",
                    code="DUPLICATE_INTERACTION",
                    status_code=status.HTTP_409_CONFLICT
                )
        return error_response(
            "Invalid interaction data.",
            code="VALIDATION_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=serializer.errors
        )

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