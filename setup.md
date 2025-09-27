# 🐍 Django Project

A Django-based web application for [short project description here].  

---

## 📦 Tech Stack
- [Django 5.x](https://www.djangoproject.com/)
- [PostgreSQL](https://www.postgresql.org/)
- [Docker & Docker Compose](https://docs.docker.com/)
- Python 3.11+

---

## 🚀 Getting Started

### 1. Prerequisites
Make sure you have the following installed:
- Python 3.11+
- pip
- Virtualenv (`python3 -m venv venv`)
- PostgreSQL (if not using Docker)
- Git

---

### 2. Clone the Repository
```bash
git clone https://github.com/PantheraNestah/alx-project-nexus.git
cd alx-project-nexus
cd movie_app_backend
```

**Project Structure**
```bash
movie_app_backend/
│── manage.py
│── requirements.txt
│── .env.example
│── docker-compose.yml
│── movie_app_backend/
|   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│── core/
|   ├── management/
│   ├── migrations/
|   ├── __init__.py
|   ├── admin.py
|   ├── apps.py
|   ├── models.py
|   ├── permissions.py
|   ├── serializers.py
|   ├── tests.py
|   ├── urls.py
|   ├── utils.py
|   └── views.py
│── templates/
└── static/

```


### 3. Setup Environment and Variables


### 4. Install Dependencies
```
pip install -r requirements.txt
```

### 5. Database Setup

### 6. Seed Movie Genres Data
```
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
