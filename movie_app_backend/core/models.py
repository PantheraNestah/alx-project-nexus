import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser

# 1. Role Model
class Role(models.Model):
    name = models.CharField(max_length=50, unique=True, help_text="Name of the role (e.g., 'user', 'admin')")

    def __str__(self):
        return self.name

# 2. Custom User Model
class User(AbstractUser):
    # We don't need name, email, password as AbstractUser has them.
    # We also get username, first_name, last_name, is_staff, is_active, is_superuser
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date_of_birth = models.DateField(null=True, blank=True)
    roles = models.ManyToManyField(Role, related_name="users")

    def __str__(self):
        return self.username

# 3. Genre Model
class Genre(models.Model):
    # Using the TMDb genre ID as our primary key
    id = models.IntegerField(primary_key=True, help_text="The genre ID from TMDb.")
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

# 4. Movie Model
class Movie(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tmdb_id = models.IntegerField(unique=True, help_text="The movie ID from TMDb.")
    title = models.CharField(max_length=255)
    overview = models.TextField(null=True, blank=True)
    poster_path = models.CharField(max_length=255, null=True, blank=True)
    release_date = models.DateField(null=True, blank=True)
    popularity = models.FloatField(default=0.0)
    vote_average = models.FloatField(default=0.0)
    
    # Many-to-Many relationship with Genre
    genres = models.ManyToManyField(Genre, related_name="movies")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.release_date.year if self.release_date else 'N/A'})"

# 5. User-Movie Interaction Model
class UserMovieInteraction(models.Model):
    class InteractionType(models.TextChoices):
        LIKED = 'LIKED', 'Liked'
        BOOKMARKED = 'BOOKMARKED', 'Bookmarked'
        WATCHED = 'WATCHED', 'Watched'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="interactions")
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="interactions")
    interaction_type = models.CharField(max_length=20, choices=InteractionType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ensures a user cannot 'like' the same movie twice
        unique_together = ('user', 'movie', 'interaction_type')

    def __str__(self):
        return f"{self.user.username} - {self.interaction_type} - {self.movie.title}"