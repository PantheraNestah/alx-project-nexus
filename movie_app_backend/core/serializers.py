from rest_framework import serializers
from .models import User, Movie, Genre, UserMovieInteraction, Role

# --- Auth & User ---
class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2', 'date_of_birth')
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return data

    def create(self, validated_data):
        validated_data.pop('password2') # Remove password2
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            date_of_birth=validated_data.get('date_of_birth')
        )
        # Assign default 'user' role
        user_role, created = Role.objects.get_or_create(name='user')
        user.roles.add(user_role)
        return user

class UserProfileSerializer(serializers.ModelSerializer):
    roles = serializers.StringRelatedField(many=True) # Display role names

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'date_of_birth', 'roles', 'date_joined')
        read_only_fields = ('id', 'username', 'email', 'roles', 'date_joined')

# --- Movie Data ---
class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ('id', 'name')

class MovieSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True) # Nested serializer for genres

    class Meta:
        model = Movie
        fields = ('id', 'tmdb_id', 'title', 'overview', 'poster_path', 'release_date', 'popularity', 'vote_average', 'genres')
        read_only_fields = ('id', 'tmdb_id', 'genres', 'popularity', 'vote_average') # tmdb_id etc. are managed internally

# --- User Interactions ---
class UserMovieInteractionSerializer(serializers.ModelSerializer):
    movie_title = serializers.CharField(source='movie.title', read_only=True)
    # You might want to include more movie details here or a nested movie serializer

    class Meta:
        model = UserMovieInteraction
        fields = ('id', 'movie', 'movie_title', 'interaction_type', 'created_at')
        read_only_fields = ('id', 'created_at', 'movie_title') # user is set by the view
        # The 'movie' field here would take a Movie ID from the frontend.

# --- Admin ---
class AdminUserSerializer(serializers.ModelSerializer):
    roles = serializers.StringRelatedField(many=True) # Display role names

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'is_active', 'is_staff', 'date_joined', 'roles')

class AssignRoleSerializer(serializers.Serializer):
    user_id = serializers.UUIDField(required=True)
    role_name = serializers.CharField(required=True, max_length=50)