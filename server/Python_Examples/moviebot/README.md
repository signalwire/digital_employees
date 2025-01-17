# Building a Movie Expert AI Agent with SignalWire AI Gateway

## Table of Contents

1. [Introduction](#introduction)
2. [Overview](#overview)
3. [SignalWire AI Gateway Functions](#signalwire-ai-gateway-functions)
   - [Function: `search_movie`](#function-search_movie)
   - [Function: `get_movie_details`](#function-get_movie_details)
   - [Function: `discover_movies`](#function-discover_movies)
   - [Function: `get_trending_movies`](#function-get_trending_movies)
   - [Function: `get_movie_recommendations`](#function-get_movie_recommendations)
   - [Function: `get_movie_credits`](#function-get_movie_credits)
   - [Function: `get_person_details`](#function-get_person_details)
   - [Function: `get_genre_list`](#function-get_genre_list)
   - [Function: `get_upcoming_movies`](#function-get_upcoming_movies)
   - [Function: `get_now_playing_movies`](#function-get_now_playing_movies)
   - [Function: `get_similar_movies`](#function-get_similar_movies)
   - [Function: `multi_search`](#function-multi_search)
4. [Environment Variables](#environment-variables)
5. [Sample Prompt for the AI Agent](#sample-prompt-for-the-ai-agent)
6. [Conclusion](#conclusion)
7. [Appendix: TMDb API Integration Notes](#appendix-tmdb-api-integration-notes)

---

## Introduction

This document outlines a detailed plan to build a movie expert AI agent using SignalWire AI Gateway (SWAIG), OpenAI's GPT models, and The Movie Database (TMDb) API. The AI agent will interact with users via SignalWire's communication channels and provide up-to-date movie information, recommendations, and personalized interactions.

---

## Overview

The AI agent leverages:

- **SignalWire AI Gateway (SWAIG)**: To handle real-time communication and integrate AI functionalities.
- **OpenAI GPT Models**: Provides natural language understanding and generation capabilities via the SignalWire AI Agent framework. You can visit [SignalWire AI](https://signalwire.ai) to learn more.
- **TMDb API**: To fetch real-time movie data, ensuring the AI provides accurate and current information.

The integration involves creating SWAIG functions that interact with TMDb's API and integrating these functions into the AI agent's capabilities.

---

## SignalWire AI Gateway Functions

Below are the SWAIG functions and arguments needed for each tool required by the AI agent. Each function corresponds to specific endpoints from TMDb's API and will be used by the AI agent to fetch and process movie data.

### Function: `search_movie`

**Purpose**: Search for movies by title.

**Definition**:

```json
{
  "name": "search_movie",
  "purpose": "Search for movies by title.",
  "argument": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "The movie title to search for."
      },
      "language": {
        "type": "string",
        "description": "Language of the results.",
        "default": "en-US"
      }
    },
    "required": ["query"]
  }
}
```

**Usage**:

When a user asks about a specific movie, this function retrieves relevant movie data.

### Function: `get_movie_details`

**Purpose**: Get detailed information about a specific movie.

**Definition**:

```json
{
  "name": "get_movie_details",
  "purpose": "Retrieve detailed information about a movie.",
  "argument": {
    "type": "object",
    "properties": {
      "movie_id": {
        "type": "integer",
        "description": "The TMDb ID of the movie."
      },
      "language": {
        "type": "string",
        "description": "Language of the results.",
        "default": "en-US"
      }
    },
    "required": ["movie_id"]
  }
}
```

**Usage**:

Provides comprehensive details when users request information about a specific movie.

### Function: `discover_movies`

**Purpose**: Discover movies based on various criteria.

**Definition**:

```json
{
  "name": "discover_movies",
  "purpose": "Discover movies by different criteria.",
  "argument": {
    "type": "object",
    "properties": {
      "with_genres": {
        "type": "string",
        "description": "Comma-separated genre IDs to filter by."
      },
      "primary_release_year": {
        "type": "integer",
        "description": "Filter movies released in a specific year."
      },
      "sort_by": {
        "type": "string",
        "description": "Sort results by criteria.",
        "default": "popularity.desc"
      },
      "language": {
        "type": "string",
        "description": "Language of the results.",
        "default": "en-US"
      }
    },
    "required": []
  }
}
```

**Usage**:

Generates personalized recommendations based on user preferences.

### Function: `get_trending_movies`

**Purpose**: Get a list of trending movies.

**Definition**:

```json
{
  "name": "get_trending_movies",
  "purpose": "Retrieve a list of movies that are currently trending.",
  "argument": {
    "type": "object",
    "properties": {
      "time_window": {
        "type": "string",
        "description": "Time window to fetch trends for ('day' or 'week').",
        "default": "week"
      },
      "language": {
        "type": "string",
        "description": "Language of the results.",
        "default": "en-US"
      }
    },
    "required": []
  }
}
```

**Usage**:

Informs users about movies that are currently popular.

### Function: `get_movie_recommendations`

**Purpose**: Get movie recommendations based on a specific movie.

**Definition**:

```json
{
  "name": "get_movie_recommendations",
  "purpose": "Get recommendations based on a specific movie.",
  "argument": {
    "type": "object",
    "properties": {
      "movie_id": {
        "type": "integer",
        "description": "The TMDb ID of the movie."
      },
      "language": {
        "type": "string",
        "description": "Language of the results.",
        "default": "en-US"
      }
    },
    "required": ["movie_id"]
  }
}
```

**Usage**:

Suggests similar movies when a user expresses interest in a particular film.

### Function: `get_movie_credits`

**Purpose**: Get cast and crew information for a movie.

**Definition**:

```json
{
  "name": "get_movie_credits",
  "purpose": "Retrieve cast and crew information for a movie.",
  "argument": {
    "type": "object",
    "properties": {
      "movie_id": {
        "type": "integer",
        "description": "The TMDb ID of the movie."
      },
      "language": {
        "type": "string",
        "description": "Language of the results.",
        "default": "en-US"
      }
    },
    "required": ["movie_id"]
  }
}
```

**Usage**:

Provides details about actors and directors when requested.

### Function: `get_person_details`

**Purpose**: Get detailed information about a person (actor, director).

**Definition**:

```json
{
  "name": "get_person_details",
  "purpose": "Retrieve detailed information about a person.",
  "argument": {
    "type": "object",
    "properties": {
      "person_id": {
        "type": "integer",
        "description": "The TMDb ID of the person."
      },
      "language": {
        "type": "string",
        "description": "Language of the results.",
        "default": "en-US"
      }
    },
    "required": ["person_id"]
  }
}
```

**Usage**:

Fetches biographies and filmographies when users inquire about specific individuals.

### Function: `get_genre_list`

**Purpose**: Get a list of movie genres.

**Definition**:

```json
{
  "name": "get_genre_list",
  "purpose": "Retrieve the list of official genres.",
  "argument": {
    "type": "object",
    "properties": {
      "language": {
        "type": "string",
        "description": "Language of the results.",
        "default": "en-US"
      }
    },
    "required": []
  }
}
```

**Usage**:

Helps in mapping genre names to IDs for filtering movies.

### Function: `get_upcoming_movies`

**Purpose**: Get a list of upcoming movies.

**Definition**:

```json
{
  "name": "get_upcoming_movies",
  "purpose": "Retrieve movies that are soon to be released.",
  "argument": {
    "type": "object",
    "properties": {
      "language": {
        "type": "string",
        "description": "Language of the results.",
        "default": "en-US"
      },
      "region": {
        "type": "string",
        "description": "Specify a region to filter release dates."
      }
    },
    "required": []
  }
}
```

**Usage**:

Informs users about movies that will be released in the near future.

### Function: `get_now_playing_movies`

**Purpose**: Get a list of movies currently playing in theaters.

**Definition**:

```json
{
  "name": "get_now_playing_movies",
  "purpose": "Retrieve movies currently playing in theaters.",
  "argument": {
    "type": "object",
    "properties": {
      "language": {
        "type": "string",
        "description": "Language of the results.",
        "default": "en-US"
      },
      "region": {
        "type": "string",
        "description": "Specify a region to filter release dates."
      }
    },
    "required": []
  }
}
```

**Usage**:

Provides users with options that are currently available in cinemas.

### Function: `get_similar_movies`

**Purpose**: Get a list of movies similar to a specified movie.

**Definition**:

```json
{
  "name": "get_similar_movies",
  "purpose": "Retrieve movies similar to a specified movie.",
  "argument": {
    "type": "object",
    "properties": {
      "movie_id": {
        "type": "integer",
        "description": "The TMDb ID of the movie."
      },
      "language": {
        "type": "string",
        "description": "Language of the results.",
        "default": "en-US"
      }
    },
    "required": ["movie_id"]
  }
}
```

**Usage**:

Offers alternatives to a movie the user is interested in.

### Function: `multi_search`

**Purpose**: Perform a multi-search across movies, TV shows, and people.

**Definition**:

```json
{
  "name": "multi_search",
  "purpose": "Search for movies, TV shows, and people with a single query.",
  "argument": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "The search query."
      },
      "language": {
        "type": "string",
        "description": "Language of the results.",
        "default": "en-US"
      }
    },
    "required": ["query"]
  }
}
```

**Usage**:

Handles broad searches when the user's intent is not specific.

---

## Environment Variables

The application requires the following environment variables to be set:

- **TMDB_API_KEY**: Your API key for accessing TMDb.
- **HTTP_USERNAME**: The username for HTTP Basic Authentication.
- **HTTP_PASSWORD**: The password for HTTP Basic Authentication.

Ensure these variables are securely stored and accessed by the application to maintain security and functionality.

---

## Sample Prompt for the AI Agent

Below is a sample system prompt that informs the AI agent of its capabilities, including the functions it can use to fetch real-time data from TMDb via the SWAIG functions.

---

**System Prompt**:

```
You are a movie expert AI assistant capable of providing detailed information about movies, directors, actors, genres, and personalized recommendations. You have access to the following functions to retrieve up-to-date movie data:

1. search_movie: Search for movies by title.
   - Parameters: query, language (default: "en-US")

2. get_movie_details: Retrieve detailed information about a movie.
   - Parameters: movie_id, language (default: "en-US")

3. discover_movies: Discover movies by different criteria.
   - Parameters: with_genres, primary_release_year, sort_by (default: "popularity.desc"), language (default: "en-US")

4. get_trending_movies: Retrieve a list of movies that are currently trending.
   - Parameters: time_window (default: "week"), language (default: "en-US")

5. get_movie_recommendations: Get recommendations based on a specific movie.
   - Parameters: movie_id, language (default: "en-US")

6. get_movie_credits: Retrieve cast and crew information for a movie.
   - Parameters: movie_id, language (default: "en-US")

7. get_person_details: Retrieve detailed information about a person.
   - Parameters: person_id, language (default: "en-US"), append_to_response

8. get_genre_list: Retrieve the list of official genres.
   - Parameters: language (default: "en-US")

9. get_upcoming_movies: Retrieve movies that are soon to be released.
   - Parameters: language (default: "en-US"), region

10. get_now_playing_movies: Retrieve movies currently playing in theaters.
    - Parameters: language (default: "en-US"), region

11. get_similar_movies: Retrieve movies similar to a specified movie.
    - Parameters: movie_id, language (default: "en-US")

12. multi_search: Search for movies, TV shows, and people with a single query.
    - Parameters: query, language (default: "en-US")

When a user asks a question, determine if any of these functions can help provide the most accurate and up-to-date information. If so, use the appropriate function to fetch the data before crafting your response.

Guidelines:

- Always provide accurate and helpful information.
- Use the latest data from the functions whenever possible.
- Maintain a conversational and friendly tone.
- Respect user preferences and provide personalized recommendations.
- Adhere to OpenAI's policies and avoid disallowed content.

Example:

- User: "Can you recommend a good sci-fi movie from last year?"
- Assistant:
  1. Use `discover_movies` with `with_genres` set to the genre ID for sci-fi and `primary_release_year` set to last year.
  2. Fetch the list of movies.
  3. Recommend a movie from the list with a brief description.

---

## Conclusion

By integrating these SWAIG functions into your AI agent, you enable it to access real-time movie data, enhancing its ability to provide accurate and personalized responses. The agent uses these functions to fetch data from TMDb as needed, ensuring users receive the most current information.

---

## Appendix: TMDb API Integration Notes

- **API Key Management**: Store your TMDb API key securely and do not expose it in code repositories.
- **Rate Limiting**: Be mindful of TMDb's API rate limits to avoid service interruptions.
- **Attribution**: Include proper attribution to TMDb as per their [terms of use](https://www.themoviedb.org/documentation/api/terms-of-use).
- **Error Handling**: Implement robust error handling to manage API errors gracefully.
- **Localization**: Utilize the `language` parameter to support users in different locales.

---

**Note**: Replace `YOUR_API_KEY` with your actual TMDb API key in your code. Ensure compliance with all relevant terms and policies when using external APIs and handling user data.
