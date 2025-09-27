from django.urls import path
from .views import (
    register_user, UserProfileView,
    TrendingMoviesView, MovieDetailView, MovieDetailByTmdbIdView,
    MovieRecommendationsView, MovieSearchView,
    UserInteractionsView, UserInteractionDetailView, UserRecommendationsView,
    AdminUserListView, AdminUserDetailView, AdminRoleAssignmentView
    , CustomTokenObtainPairView, 
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Auth & User
    path('auth/register/', register_user, name='register'),
    path('auth/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('user/profile/', UserProfileView.as_view(), name='user_profile'),
    path('user/profile/update/', UserProfileView.as_view(), name='user_profile_update'), # PUT for update

    # Movie Data
    path('movies/trending/', TrendingMoviesView.as_view(), name='trending_movies'),
    path('movies/<uuid:movie_id>/', MovieDetailView.as_view(), name='movie_detail'), # Our internal UUID
    path('movies/tmdb/<int:tmdb_id>/', MovieDetailByTmdbIdView.as_view(), name='movie_detail_by_tmdb_id'),
    path('movies/<uuid:movie_id>/recommendations/', MovieRecommendationsView.as_view(), name='movie_recommendations'),
    path('movies/search/', MovieSearchView.as_view(), name='movie_search'),

    # User Interactions & Recommendations
    path('user/interactions/', UserInteractionsView.as_view(), name='user_interactions'),
    path('user/interactions/<int:interaction_id>/', UserInteractionDetailView.as_view(), name='user_interaction_detail'), # DELETE
    path('user/recommendations/', UserRecommendationsView.as_view(), name='user_recommendations'),

    # Admin Endpoints
    path('admin/users/', AdminUserListView.as_view(), name='admin_user_list'),
    path('admin/users/<uuid:user_id>/', AdminUserDetailView.as_view(), name='admin_user_detail'), # DELETE
    path('admin/roles/assign/', AdminRoleAssignmentView.as_view(), name='admin_assign_role'),
]