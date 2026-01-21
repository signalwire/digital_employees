# CineBot

An AI-powered movie discovery assistant that enables natural voice conversations about films. Users can search for movies, explore actors and directors, browse by genre, get recommendations, and access streaming availability.

## Source Repository

The full source code is maintained in a separate repository:

**[github.com/signalwire-demos/cinebot](https://github.com/signalwire-demos/cinebot)**

## Features

- **Voice Interaction** - Natural language understanding with ElevenLabs voice synthesis
- **Animated Agent** - Visual AI avatar during conversations
- **Movie Search** - Title searches with automatic year filtering
- **Trending Content** - Browse trending movies by day or week
- **Genre Browsing** - Explore major movie categories
- **Detailed Info** - Cast, crew, ratings, plot summaries, streaming availability
- **Personalized Recommendations** - Based on viewing history

## Architecture

- **Backend**: Python with SignalWire Agents SDK
- **Movie Data**: tmdbsimple for The Movie Database API
- **Caching**: Redis for intelligent caching
- **Frontend**: JavaScript with WebRTC, Netflix-style responsive design
- **Deployment**: Docker-compatible

## Getting Started

See the [main repository](https://github.com/signalwire-demos/cinebot) for setup and deployment instructions.
