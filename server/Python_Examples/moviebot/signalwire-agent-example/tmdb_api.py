"""
TMDB API module for MovieBot.

This module provides functions to interact with The Movie Database (TMDB) API.
"""

import requests
from typing import Dict, Any, Optional

# TMDB API base URL
TMDB_API_BASE_URL = "https://api.themoviedb.org/3"

def tmdb_request(api_key: str, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Make a request to the TMDB API.
    
    Args:
        api_key: The TMDB API key
        endpoint: The API endpoint to call
        params: Additional parameters for the request
        
    Returns:
        JSON response as dictionary
    """
    url = f"{TMDB_API_BASE_URL}{endpoint}"
    
    # Prepare request parameters
    request_params = params.copy() if params else {}
    request_params["api_key"] = api_key
    
    try:
        response = requests.get(url, params=request_params)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"TMDB API request failed: {e}")
        return {"error": str(e)}

def search_movie(api_key: str, query: str, language: str = "en-US") -> Dict[str, Any]:
    """
    Search for movies by title.
    
    Args:
        api_key: TMDB API key
        query: Movie title to search for
        language: Language for results
        
    Returns:
        Dictionary containing search results
    """
    endpoint = "/search/movie"
    params = {
        "query": query,
        "language": language,
        "include_adult": "false"
    }
    return tmdb_request(api_key, endpoint, params)

def get_movie_details(api_key: str, movie_id: int, language: str = "en-US") -> Dict[str, Any]:
    """
    Get detailed information about a specific movie.
    
    Args:
        api_key: TMDB API key
        movie_id: TMDB movie ID
        language: Language for results
        
    Returns:
        Dictionary containing movie details
    """
    endpoint = f"/movie/{movie_id}"
    params = {"language": language}
    return tmdb_request(api_key, endpoint, params)

def discover_movies(
    api_key: str, 
    with_genres: Optional[str] = None, 
    primary_release_year: Optional[int] = None,
    sort_by: str = "popularity.desc", 
    language: str = "en-US"
) -> Dict[str, Any]:
    """
    Discover movies based on different criteria.
    
    Args:
        api_key: TMDB API key
        with_genres: Comma-separated list of genre IDs
        primary_release_year: Filter by release year
        sort_by: Sort method (popularity.desc, vote_average.desc, etc.)
        language: Language for results
        
    Returns:
        Dictionary containing discovered movies
    """
    endpoint = "/discover/movie"
    params = {
        "sort_by": sort_by,
        "language": language
    }
    
    if with_genres:
        params["with_genres"] = with_genres
    if primary_release_year:
        params["primary_release_year"] = primary_release_year
        
    return tmdb_request(api_key, endpoint, params)

def get_trending_movies(api_key: str, time_window: str = "week", language: str = "en-US") -> Dict[str, Any]:
    """
    Get a list of trending movies.
    
    Args:
        api_key: TMDB API key
        time_window: Time window for trending calculation (day or week)
        language: Language for results
        
    Returns:
        Dictionary containing trending movies
    """
    endpoint = f"/trending/movie/{time_window}"
    params = {"language": language}
    return tmdb_request(api_key, endpoint, params)

def get_movie_recommendations(api_key: str, movie_id: int, language: str = "en-US") -> Dict[str, Any]:
    """
    Get movie recommendations based on a specific movie.
    
    Args:
        api_key: TMDB API key
        movie_id: TMDB movie ID
        language: Language for results
        
    Returns:
        Dictionary containing recommended movies
    """
    endpoint = f"/movie/{movie_id}/recommendations"
    params = {"language": language}
    return tmdb_request(api_key, endpoint, params)

def get_movie_credits(api_key: str, movie_id: int, language: str = "en-US") -> Dict[str, Any]:
    """
    Get cast and crew information for a movie.
    
    Args:
        api_key: TMDB API key
        movie_id: TMDB movie ID
        language: Language for results
        
    Returns:
        Dictionary containing movie credits
    """
    endpoint = f"/movie/{movie_id}/credits"
    params = {"language": language}
    return tmdb_request(api_key, endpoint, params)

def get_person_details(api_key: str, person_id: int, language: str = "en-US") -> Dict[str, Any]:
    """
    Get detailed information about a person.
    
    Args:
        api_key: TMDB API key
        person_id: TMDB person ID
        language: Language for results
        
    Returns:
        Dictionary containing person details
    """
    endpoint = f"/person/{person_id}"
    params = {
        "language": language,
        "append_to_response": "movie_credits"
    }
    return tmdb_request(api_key, endpoint, params)

def get_genre_list(api_key: str, language: str = "en-US") -> Dict[str, Any]:
    """
    Get the list of official genres.
    
    Args:
        api_key: TMDB API key
        language: Language for results
        
    Returns:
        Dictionary containing genre list
    """
    endpoint = "/genre/movie/list"
    params = {"language": language}
    return tmdb_request(api_key, endpoint, params)

def get_upcoming_movies(api_key: str, language: str = "en-US", region: str = "US") -> Dict[str, Any]:
    """
    Get a list of upcoming movies.
    
    Args:
        api_key: TMDB API key
        language: Language for results
        region: Region code (ISO 3166-1)
        
    Returns:
        Dictionary containing upcoming movies
    """
    endpoint = "/movie/upcoming"
    params = {
        "language": language,
        "region": region
    }
    return tmdb_request(api_key, endpoint, params)

def get_now_playing_movies(api_key: str, language: str = "en-US", region: str = "US") -> Dict[str, Any]:
    """
    Get a list of movies currently in theaters.
    
    Args:
        api_key: TMDB API key
        language: Language for results
        region: Region code (ISO 3166-1)
        
    Returns:
        Dictionary containing now playing movies
    """
    endpoint = "/movie/now_playing"
    params = {
        "language": language,
        "region": region
    }
    return tmdb_request(api_key, endpoint, params)

def get_similar_movies(api_key: str, movie_id: int, language: str = "en-US") -> Dict[str, Any]:
    """
    Get a list of similar movies.
    
    Args:
        api_key: TMDB API key
        movie_id: TMDB movie ID
        language: Language for results
        
    Returns:
        Dictionary containing similar movies
    """
    endpoint = f"/movie/{movie_id}/similar"
    params = {"language": language}
    return tmdb_request(api_key, endpoint, params)

def multi_search(api_key: str, query: str, language: str = "en-US") -> Dict[str, Any]:
    """
    Search for movies, TV shows, and people.
    
    Args:
        api_key: TMDB API key
        query: Search query
        language: Language for results
        
    Returns:
        Dictionary containing search results
    """
    endpoint = "/search/multi"
    params = {
        "query": query,
        "language": language,
        "include_adult": "false"
    }
    return tmdb_request(api_key, endpoint, params) 