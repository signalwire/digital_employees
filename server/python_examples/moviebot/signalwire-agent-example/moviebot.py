#!/usr/bin/env python3
"""
MovieBot - An AI agent that provides movie information using TMDB API.

This agent demonstrates how to build a specialized AI agent using the SignalWire AI Agents SDK
that interacts with a third-party API (The Movie Database) to provide real-time movie data.
"""

import os
import json
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional

from signalwire_agents import AgentBase
from signalwire_agents.core.function_result import SwaigFunctionResult
from tmdb_api import (
    search_movie, get_movie_details, discover_movies, get_trending_movies,
    get_movie_recommendations, get_movie_credits, get_person_details,
    get_genre_list, get_upcoming_movies, get_now_playing_movies,
    get_similar_movies, multi_search
)

class MovieBot(AgentBase):
    """
    AI Agent specialized in providing movie information using TMDB API.
    
    Features:
    - Movie search and detailed information
    - Trending and upcoming movie recommendations
    - Actor and director information
    - Genre-based movie discovery
    """
    
    def __init__(self, tmdb_api_key: str, **kwargs):
        """
        Initialize the MovieBot agent.
        
        Args:
            tmdb_api_key: API key for The Movie Database
            **kwargs: Additional arguments to pass to AgentBase
        """
        # Initialize with default settings or override with provided kwargs
        kwargs.setdefault('name', 'moviebot')
        kwargs.setdefault('route', '/moviebot')
        
        super().__init__(**kwargs)
        
        # Store API key for use in tools
        self.tmdb_api_key = tmdb_api_key
        
        # Configure agent personality and behavior using POM
        self._configure_prompt()
        
        # Add hints for movie-related terms
        self._add_movie_hints()
        
        # Set voice to something engaging
        self.add_language(
            name="English",
            code="en-US",
            voice="elevenlabs.josh",
            function_fillers=["I'm searching for movie information...", "Let me find that..."]
        )
        
        # Set AI parameters
        self.set_params({
            "end_of_speech_timeout": 1000
        })
    
    def _configure_prompt(self):
        """Configure the agent's prompt using POM."""
        
        # Personality section
        self.prompt_add_section(
            "Personality",
            body="You are MovieBot, a friendly and knowledgeable movie expert. You're passionate about films "
                 "and love to discuss all aspects of cinema including plots, actors, directors, genres, "
                 "and making recommendations based on user preferences."
        )
        
        # Goal section
        self.prompt_add_section(
            "Goal",
            body="Help users discover movies, learn about films they're interested in, and find "
                 "recommendations based on their tastes. Provide accurate and up-to-date information "
                 "about movies, actors, directors, and current releases."
        )
        
        # Instructions section
        self.prompt_add_section(
            "Instructions",
            bullets=[
                "Always use the available tools to get accurate and current movie information",
                "When a user asks about a movie, search for it and provide details",
                "For specific actors or directors, look up their filmography and information",
                "When recommending movies, ask about user preferences first (genres, actors, etc.)",
                "If a user mentions a movie but you're not sure which one, use search to clarify",
                "Provide concise but informative responses that focus on the user's question",
                "If information is not available or unclear, be honest about limitations",
                "When listing movies, include the year of release for clarity",
                "For trending or popular movie requests, use get_trending_movies",
                "For current movies in theaters, use get_now_playing_movies"
            ]
        )
        
        # Knowledge section with API details
        self.prompt_add_section(
            "Knowledge",
            body="You have access to The Movie Database (TMDB) API through various tools. These tools "
                 "allow you to search for movies, get details about specific films, find similar movies, "
                 "get information about actors and directors, and discover trending or upcoming releases."
        )
    
    def _add_movie_hints(self):
        """Add hints for common movie-related terms."""
        self.add_hints([
            "TMDB", "MCU", "Marvel", "DC", "Oscar", "Academy Award",
            "Hollywood", "Bollywood", "Netflix", "HBO", "Disney+"
        ])
        
        # Add pronunciation rules for common abbreviations
        self.add_pronunciation("MCU", "M C U", ignore_case=True)
        self.add_pronunciation("TMDB", "T M D B", ignore_case=True)
        self.add_pronunciation("IMDB", "I M D B", ignore_case=True)
    
    @AgentBase.tool(
        name="search_movie",
        description="Search for movies by title",
        parameters={
            "query": {
                "type": "string",
                "description": "The movie title to search for"
            },
            "language": {
                "type": "string",
                "description": "Language of the results",
                "default": "en-US"
            }
        }
    )
    def search_movie_tool(self, args, raw_data):
        """Search for movies by title."""
        query = args.get("query", "")
        language = args.get("language", "en-US")
        
        result = search_movie(self.tmdb_api_key, query, language)
        
        # Format the results in a readable way
        if not result.get("results"):
            return SwaigFunctionResult(f"No movies found for '{query}'.")
        
        formatted_results = "I found the following movies:\n\n"
        for movie in result.get("results", [])[:5]:  # Limit to top 5 results
            title = movie.get("title", "Unknown title")
            year = movie.get("release_date", "")[:4] if movie.get("release_date") else "Unknown year"
            id = movie.get("id", "")
            rating = movie.get("vote_average", "No ratings")
            
            formatted_results += f"- {title} ({year}) - ID: {id}, Rating: {rating}/10\n"
        
        formatted_results += "\nYou can get more details about a specific movie by using its ID."
        return SwaigFunctionResult(formatted_results)
    
    @AgentBase.tool(
        name="get_movie_details",
        description="Retrieve detailed information about a movie",
        parameters={
            "movie_id": {
                "type": "integer",
                "description": "The TMDB ID of the movie"
            },
            "language": {
                "type": "string",
                "description": "Language of the results",
                "default": "en-US"
            }
        }
    )
    def get_movie_details_tool(self, args, raw_data):
        """Get detailed information about a specific movie."""
        movie_id = args.get("movie_id")
        language = args.get("language", "en-US")
        
        if not movie_id:
            return SwaigFunctionResult("Error: Movie ID is required.")
        
        result = get_movie_details(self.tmdb_api_key, movie_id, language)
        
        if not result or "title" not in result:
            return SwaigFunctionResult(f"No details found for movie ID {movie_id}.")
        
        # Format the movie details
        title = result.get("title", "Unknown title")
        year = result.get("release_date", "")[:4] if result.get("release_date") else "Unknown year"
        genres = ", ".join([g.get("name", "") for g in result.get("genres", [])])
        runtime = result.get("runtime", 0)
        vote_avg = result.get("vote_average", "No ratings")
        overview = result.get("overview", "No overview available.")
        
        formatted_details = f"**{title}** ({year})\n\n"
        formatted_details += f"**Genre:** {genres}\n"
        formatted_details += f"**Runtime:** {runtime} minutes\n"
        formatted_details += f"**Rating:** {vote_avg}/10\n\n"
        formatted_details += f"**Overview:**\n{overview}\n"
        
        return SwaigFunctionResult(formatted_details)
    
    @AgentBase.tool(
        name="get_trending_movies",
        description="Retrieve a list of movies that are currently trending",
        parameters={
            "time_window": {
                "type": "string",
                "description": "Time window for trending calculation (day or week)",
                "enum": ["day", "week"],
                "default": "week"
            },
            "language": {
                "type": "string",
                "description": "Language of the results",
                "default": "en-US"
            }
        }
    )
    def get_trending_movies_tool(self, args, raw_data):
        """Get currently trending movies."""
        time_window = args.get("time_window", "week")
        language = args.get("language", "en-US")
        
        result = get_trending_movies(self.tmdb_api_key, time_window, language)
        
        if not result.get("results"):
            return SwaigFunctionResult("No trending movies found.")
        
        formatted_results = f"Here are the trending movies for this {time_window}:\n\n"
        for movie in result.get("results", [])[:10]:  # Limit to top 10 results
            title = movie.get("title", "Unknown title")
            year = movie.get("release_date", "")[:4] if movie.get("release_date") else "Unknown year"
            rating = movie.get("vote_average", "No ratings")
            
            formatted_results += f"- {title} ({year}) - Rating: {rating}/10\n"
        
        return SwaigFunctionResult(formatted_results)

    @AgentBase.tool(
        name="get_now_playing_movies",
        description="Retrieve movies currently playing in theaters",
        parameters={
            "language": {
                "type": "string",
                "description": "Language of the results",
                "default": "en-US"
            },
            "region": {
                "type": "string",
                "description": "Specify a region to filter release dates",
                "default": "US"
            }
        }
    )
    def get_now_playing_movies_tool(self, args, raw_data):
        """Get movies that are currently in theaters."""
        language = args.get("language", "en-US")
        region = args.get("region", "US")
        
        result = get_now_playing_movies(self.tmdb_api_key, language, region)
        
        if not result.get("results"):
            return SwaigFunctionResult("No movies currently playing in theaters found.")
        
        formatted_results = "Movies currently playing in theaters:\n\n"
        for movie in result.get("results", [])[:10]:  # Limit to top 10 results
            title = movie.get("title", "Unknown title")
            rating = movie.get("vote_average", "No ratings")
            
            formatted_results += f"- {title} - Rating: {rating}/10\n"
        
        return SwaigFunctionResult(formatted_results)

    @AgentBase.tool(
        name="get_upcoming_movies",
        description="Retrieve movies that are soon to be released",
        parameters={
            "language": {
                "type": "string",
                "description": "Language of the results",
                "default": "en-US"
            },
            "region": {
                "type": "string",
                "description": "Specify a region to filter release dates",
                "default": "US"
            }
        }
    )
    def get_upcoming_movies_tool(self, args, raw_data):
        """Get movies that will be released soon."""
        language = args.get("language", "en-US")
        region = args.get("region", "US")
        
        result = get_upcoming_movies(self.tmdb_api_key, language, region)
        
        if not result.get("results"):
            return SwaigFunctionResult("No upcoming movie releases found.")
        
        formatted_results = "Upcoming movie releases:\n\n"
        for movie in result.get("results", [])[:10]:  # Limit to top 10 results
            title = movie.get("title", "Unknown title")
            release_date = movie.get("release_date", "Unknown date")
            
            formatted_results += f"- {title} - Releasing on: {release_date}\n"
        
        return SwaigFunctionResult(formatted_results)

    @AgentBase.tool(
        name="get_person_details",
        description="Retrieve detailed information about a person",
        parameters={
            "person_id": {
                "type": "integer",
                "description": "The TMDB ID of the person"
            },
            "language": {
                "type": "string",
                "description": "Language of the results",
                "default": "en-US"
            }
        }
    )
    def get_person_details_tool(self, args, raw_data):
        """Get detailed information about a person."""
        person_id = args.get("person_id")
        language = args.get("language", "en-US")
        
        if not person_id:
            return SwaigFunctionResult("Error: Person ID is required.")
        
        result = get_person_details(self.tmdb_api_key, person_id, language)
        
        if not result or "name" not in result:
            return SwaigFunctionResult(f"No details found for person ID {person_id}.")
        
        # Format the person details
        name = result.get("name", "Unknown name")
        birthday = result.get("birthday", "Unknown")
        known_for = result.get("known_for_department", "Unknown")
        biography = result.get("biography", "No biography available.")
        
        # Get the person's movie credits
        movie_credits = result.get("movie_credits", {})
        cast_roles = movie_credits.get("cast", [])
        crew_roles = movie_credits.get("crew", [])
        
        formatted_details = f"**{name}**\n\n"
        formatted_details += f"**Birthday:** {birthday}\n"
        formatted_details += f"**Known for:** {known_for}\n\n"
        formatted_details += f"**Biography:**\n{biography}\n\n"
        
        # Add notable cast roles (limit to 5)
        if cast_roles:
            formatted_details += "**Notable Acting Roles:**\n"
            for role in sorted(cast_roles, key=lambda x: x.get("popularity", 0), reverse=True)[:5]:
                title = role.get("title", "Unknown")
                character = role.get("character", "Unknown role")
                year = role.get("release_date", "")[:4] if role.get("release_date") else "Unknown year"
                formatted_details += f"- {title} ({year}) as {character}\n"
            formatted_details += "\n"
        
        # Add notable crew roles (directing, writing, etc.) - limit to 5
        if crew_roles:
            formatted_details += "**Notable Crew Roles:**\n"
            for role in sorted(crew_roles, key=lambda x: x.get("popularity", 0), reverse=True)[:5]:
                title = role.get("title", "Unknown")
                job = role.get("job", "Unknown job")
                year = role.get("release_date", "")[:4] if role.get("release_date") else "Unknown year"
                formatted_details += f"- {title} ({year}) - {job}\n"
        
        return SwaigFunctionResult(formatted_details)
    
    @AgentBase.tool(
        name="get_movie_credits",
        description="Retrieve cast and crew information for a movie",
        parameters={
            "movie_id": {
                "type": "integer",
                "description": "The TMDB ID of the movie"
            },
            "language": {
                "type": "string",
                "description": "Language of the results",
                "default": "en-US"
            }
        }
    )
    def get_movie_credits_tool(self, args, raw_data):
        """Get cast and crew information for a movie."""
        movie_id = args.get("movie_id")
        language = args.get("language", "en-US")
        
        if not movie_id:
            return SwaigFunctionResult("Error: Movie ID is required.")
        
        result = get_movie_credits(self.tmdb_api_key, movie_id, language)
        
        if not result:
            return SwaigFunctionResult(f"No credits found for movie ID {movie_id}.")
        
        # Also get movie details to include the movie title
        movie_details = get_movie_details(self.tmdb_api_key, movie_id, language)
        movie_title = movie_details.get("title", f"Movie {movie_id}")
        
        # Format the movie credits
        cast = result.get("cast", [])
        crew = result.get("crew", [])
        
        formatted_results = f"**Cast and Crew for {movie_title}**\n\n"
        
        # Add cast members (limit to 10)
        if cast:
            formatted_results += "**Cast:**\n"
            for actor in sorted(cast, key=lambda x: x.get("order", 999))[:10]:
                name = actor.get("name", "Unknown")
                character = actor.get("character", "Unknown role")
                formatted_results += f"- {name} as {character}\n"
            formatted_results += "\n"
        
        # Add key crew members (director, writer, etc.) - limit to 5
        if crew:
            # Get the directors
            directors = [c for c in crew if c.get("job") == "Director"]
            if directors:
                formatted_results += "**Director(s):**\n"
                for director in directors:
                    formatted_results += f"- {director.get('name', 'Unknown')}\n"
                formatted_results += "\n"
            
            # Get the writers
            writers = [c for c in crew if c.get("department") == "Writing"]
            if writers:
                formatted_results += "**Writers:**\n"
                for writer in writers[:3]:  # Limit to 3 writers
                    formatted_results += f"- {writer.get('name', 'Unknown')} ({writer.get('job', 'Writer')})\n"
                formatted_results += "\n"
            
            # Get other key crew members
            key_crew = [c for c in crew if c.get("job") in ["Producer", "Executive Producer", "Cinematography", "Original Music Composer"]]
            if key_crew:
                formatted_results += "**Key Crew:**\n"
                for crew_member in key_crew[:5]:  # Limit to 5 key crew members
                    formatted_results += f"- {crew_member.get('name', 'Unknown')} ({crew_member.get('job', 'Unknown')})\n"
        
        return SwaigFunctionResult(formatted_results)
    
    @AgentBase.tool(
        name="discover_movies",
        description="Discover movies by different criteria",
        parameters={
            "with_genres": {
                "type": "string",
                "description": "Comma-separated list of genre IDs"
            },
            "primary_release_year": {
                "type": "integer",
                "description": "Filter by release year"
            },
            "sort_by": {
                "type": "string",
                "description": "Sort method (popularity.desc, vote_average.desc, etc.)",
                "default": "popularity.desc"
            },
            "language": {
                "type": "string",
                "description": "Language of the results",
                "default": "en-US"
            }
        }
    )
    def discover_movies_tool(self, args, raw_data):
        """Discover movies based on different criteria."""
        with_genres = args.get("with_genres")
        primary_release_year = args.get("primary_release_year")
        sort_by = args.get("sort_by", "popularity.desc")
        language = args.get("language", "en-US")
        
        result = discover_movies(
            self.tmdb_api_key, 
            with_genres=with_genres, 
            primary_release_year=primary_release_year,
            sort_by=sort_by, 
            language=language
        )
        
        if not result.get("results"):
            return SwaigFunctionResult("No movies found matching the criteria.")
        
        # Format the filter description
        filter_description = "Discovered movies"
        if with_genres:
            # Get the genre names
            genres_result = get_genre_list(self.tmdb_api_key, language)
            genre_map = {str(g.get("id")): g.get("name") for g in genres_result.get("genres", [])}
            
            genre_names = []
            for genre_id in with_genres.split(","):
                if genre_id in genre_map:
                    genre_names.append(genre_map[genre_id])
            
            if genre_names:
                filter_description += f" in {', '.join(genre_names)}"
        
        if primary_release_year:
            filter_description += f" from {primary_release_year}"
        
        formatted_results = f"{filter_description}:\n\n"
        for movie in result.get("results", [])[:10]:  # Limit to top 10 results
            title = movie.get("title", "Unknown title")
            year = movie.get("release_date", "")[:4] if movie.get("release_date") else "Unknown year"
            rating = movie.get("vote_average", "No ratings")
            
            formatted_results += f"- {title} ({year}) - Rating: {rating}/10\n"
        
        return SwaigFunctionResult(formatted_results)
    
    @AgentBase.tool(
        name="get_similar_movies",
        description="Retrieve movies similar to a specified movie",
        parameters={
            "movie_id": {
                "type": "integer",
                "description": "The TMDB ID of the movie"
            },
            "language": {
                "type": "string",
                "description": "Language of the results",
                "default": "en-US"
            }
        }
    )
    def get_similar_movies_tool(self, args, raw_data):
        """Get movies similar to a specified movie."""
        movie_id = args.get("movie_id")
        language = args.get("language", "en-US")
        
        if not movie_id:
            return SwaigFunctionResult("Error: Movie ID is required.")
        
        # Get the movie details to include the movie title
        movie_details = get_movie_details(self.tmdb_api_key, movie_id, language)
        movie_title = movie_details.get("title", f"Movie {movie_id}")
        
        result = get_similar_movies(self.tmdb_api_key, movie_id, language)
        
        if not result.get("results"):
            return SwaigFunctionResult(f"No similar movies found for {movie_title}.")
        
        formatted_results = f"Movies similar to {movie_title}:\n\n"
        for movie in result.get("results", [])[:10]:  # Limit to top 10 results
            title = movie.get("title", "Unknown title")
            year = movie.get("release_date", "")[:4] if movie.get("release_date") else "Unknown year"
            rating = movie.get("vote_average", "No ratings")
            
            formatted_results += f"- {title} ({year}) - Rating: {rating}/10\n"
        
        return SwaigFunctionResult(formatted_results)

    @AgentBase.tool(
        name="multi_search",
        description="Search for movies, TV shows, and people with a single query",
        parameters={
            "query": {
                "type": "string",
                "description": "The search query"
            },
            "language": {
                "type": "string",
                "description": "Language of the results",
                "default": "en-US"
            }
        }
    )
    def multi_search_tool(self, args, raw_data):
        """Search for movies, TV shows, and people."""
        query = args.get("query", "")
        language = args.get("language", "en-US")
        
        result = multi_search(self.tmdb_api_key, query, language)
        
        if not result.get("results"):
            return SwaigFunctionResult(f"No results found for '{query}'.")
        
        movies = []
        people = []
        tv_shows = []
        
        # Categorize results
        for item in result.get("results", [])[:15]:  # Limit to top 15 results total
            media_type = item.get("media_type")
            
            if media_type == "movie":
                movies.append(item)
            elif media_type == "person":
                people.append(item)
            elif media_type == "tv":
                tv_shows.append(item)
        
        formatted_results = f"Search results for '{query}':\n\n"
        
        # Add movies
        if movies:
            formatted_results += "**Movies:**\n"
            for movie in movies[:5]:  # Limit to 5 movies
                title = movie.get("title", "Unknown title")
                year = movie.get("release_date", "")[:4] if movie.get("release_date") else "Unknown year"
                id = movie.get("id", "")
                
                formatted_results += f"- {title} ({year}) - ID: {id}\n"
            formatted_results += "\n"
        
        # Add people
        if people:
            formatted_results += "**People:**\n"
            for person in people[:5]:  # Limit to 5 people
                name = person.get("name", "Unknown name")
                id = person.get("id", "")
                known_for = person.get("known_for_department", "")
                
                formatted_results += f"- {name} ({known_for}) - ID: {id}\n"
            formatted_results += "\n"
        
        # Add TV shows
        if tv_shows:
            formatted_results += "**TV Shows:**\n"
            for show in tv_shows[:5]:  # Limit to 5 TV shows
                title = show.get("name", "Unknown title")
                year = show.get("first_air_date", "")[:4] if show.get("first_air_date") else "Unknown year"
                id = show.get("id", "")
                
                formatted_results += f"- {title} ({year}) - ID: {id}\n"
        
        return SwaigFunctionResult(formatted_results)
    
    @AgentBase.tool(
        name="get_movie_recommendations",
        description="Get recommendations based on a specific movie",
        parameters={
            "movie_id": {
                "type": "integer",
                "description": "The TMDB ID of the movie"
            },
            "language": {
                "type": "string",
                "description": "Language of the results",
                "default": "en-US"
            }
        }
    )
    def get_movie_recommendations_tool(self, args, raw_data):
        """Get movie recommendations based on a specific movie."""
        movie_id = args.get("movie_id")
        language = args.get("language", "en-US")
        
        if not movie_id:
            return SwaigFunctionResult("Error: Movie ID is required.")
        
        # Get the movie details to include the movie title
        movie_details = get_movie_details(self.tmdb_api_key, movie_id, language)
        movie_title = movie_details.get("title", f"Movie {movie_id}")
        
        result = get_movie_recommendations(self.tmdb_api_key, movie_id, language)
        
        if not result.get("results"):
            return SwaigFunctionResult(f"No recommendations found for {movie_title}.")
        
        formatted_results = f"If you liked {movie_title}, you might also enjoy:\n\n"
        for movie in result.get("results", [])[:10]:  # Limit to top 10 results
            title = movie.get("title", "Unknown title")
            year = movie.get("release_date", "")[:4] if movie.get("release_date") else "Unknown year"
            rating = movie.get("vote_average", "No ratings")
            
            formatted_results += f"- {title} ({year}) - Rating: {rating}/10\n"
        
        return SwaigFunctionResult(formatted_results)
    
    @AgentBase.tool(
        name="get_genre_list",
        description="Retrieve the list of official movie genres",
        parameters={
            "language": {
                "type": "string",
                "description": "Language of the results",
                "default": "en-US"
            }
        }
    )
    def get_genre_list_tool(self, args, raw_data):
        """Get the list of official movie genres."""
        language = args.get("language", "en-US")
        
        result = get_genre_list(self.tmdb_api_key, language)
        
        if not result.get("genres"):
            return SwaigFunctionResult("No genre information available.")
        
        genres = result.get("genres", [])
        
        formatted_results = "Movie Genres:\n\n"
        for genre in sorted(genres, key=lambda x: x.get("name", "")):
            name = genre.get("name", "Unknown")
            id = genre.get("id", "")
            
            formatted_results += f"- {name} (ID: {id})\n"
        
        return SwaigFunctionResult(formatted_results)

def main():
    """Run the MovieBot example."""
    import argparse
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="MovieBot Example")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=3000, help="Port to bind the server to")
    args = parser.parse_args()
    
    # Get TMDB API key from environment variable
    tmdb_api_key = os.environ.get("TMDB_API_KEY")
    if not tmdb_api_key:
        print("Error: TMDB_API_KEY environment variable is required.")
        print("Please set it with: export TMDB_API_KEY=your_api_key")
        return
    
    # Create our MovieBot agent
    agent = MovieBot(tmdb_api_key=tmdb_api_key, host=args.host, port=args.port)
    
    # Get basic auth credentials for display
    username, password = agent.get_basic_auth_credentials()
    
    # Print information about the agent
    print("Starting the MovieBot Agent")
    print("----------------------------------------")
    print(f"URL: http://{args.host}:{args.port}{agent.route}")
    print(f"Basic Auth: {username}:{password}")
    print("----------------------------------------")
    print("Press Ctrl+C to stop the agent")
    
    # Start the agent server
    agent.serve()

if __name__ == "__main__":
    main() 