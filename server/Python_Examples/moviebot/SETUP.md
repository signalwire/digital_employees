# MovieBot SignalWire AI Agent

## Overview

The MovieBot SignalWire AI Agent is a sophisticated assistant designed to provide detailed information about movies, directors, actors, genres, and personalized recommendations. It leverages the SignalWire AI Gateway (SWAIG) for real-time communication, OpenAI's GPT models for natural language processing, and The Movie Database (TMDb) API for up-to-date movie data.

## Features

- **Movie Search**: Find movies by title using the `search_movie` function.
- **Detailed Movie Information**: Retrieve comprehensive details about a movie with `get_movie_details`.
- **Movie Discovery**: Discover movies based on genres, release year, and popularity using `discover_movies`.
- **Trending Movies**: Get a list of currently trending movies with `get_trending_movies`.
- **Recommendations**: Receive movie recommendations based on a specific movie using `get_movie_recommendations`.
- **Cast and Crew Information**: Access detailed cast and crew information with `get_movie_credits`.
- **Person Details**: Fetch detailed information about actors and directors using `get_person_details`.
- **Genre List**: Retrieve a list of official movie genres with `get_genre_list`.
- **Upcoming Movies**: Get information on movies soon to be released using `get_upcoming_movies`.
- **Now Playing**: Find movies currently playing in theaters with `get_now_playing_movies`.
- **Similar Movies**: Discover movies similar to a specified movie using `get_similar_movies`.
- **Multi-Search**: Perform a broad search across movies, TV shows, and people with `multi_search`.

## Architecture

The AI agent is built on the following components:

- **SignalWire AI Gateway (SWAIG)**: Facilitates real-time communication and integrates AI functionalities.
- **OpenAI GPT Models**: Provides natural language understanding and generation capabilities via the SignalWire AI Agent framework. You can visit [SignalWire AI](https://signalwire.ai) to learn more.
- **TMDb API**: Supplies real-time movie data, ensuring the AI provides accurate and current information.

## Getting Started

### Prerequisites

- **API Key**: Obtain an API key from TMDb to access their API.
- **SignalWire Account**: Set up an account with SignalWire to use their AI Gateway.

### Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/briankwest/moviebot.git
   cd moviebot
   ```

2. **Install Dependencies**:
   Ensure you have Python and pip installed, then run:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API Keys**:
   Replace `YOUR_API_KEY` in the code with your actual TMDb API key.

### Deploying on Dokku

1. **Create a Dokku App**:
   Ensure you have Dokku installed and set up on your server. Create a new Dokku app:
   ```bash
   dokku apps:create moviebot
   ```

2. **Set Environment Variables**:
   Set the necessary environment variables, including your TMDb API key:
   ```bash
   dokku config:set moviebot TMDB_API_KEY=your_tmdb_api_key
   ```

3. **Deploy the App**:
   Add your Dokku server as a Git remote and push the code:
   ```bash
   git remote add dokku dokku@your_dokku_server:moviebot
   git push dokku main
   ```

4. **Run Migrations (if any)**:
   If your application requires database migrations, run them using:
   ```bash
   dokku run moviebot python manage.py migrate
   ```

5. **Set Up Let's Encrypt**:
   To secure your app with SSL, use Dokku's Let's Encrypt plugin. First, ensure the plugin is installed:
   ```bash
   sudo dokku plugin:install https://github.com/dokku/dokku-letsencrypt.git
   ```

   Then, enable Let's Encrypt for your app:
   ```bash
   dokku letsencrypt:enable moviebot
   ```

   To automatically renew the certificates, set up a cron job:
   ```bash
   dokku letsencrypt:cron-job --add
   ```

6. **Access the App**:
   Your app should now be running on your Dokku server with SSL enabled. Access it via the URL provided by Dokku.

### Usage

Run the AI agent using the command:
```bash
python app.py
```

Interact with the AI agent through the configured communication channels to get movie information and recommendations.

## Development

### Adding New Features

To add new features or functions, follow these steps:

1. **Define New SWAIG Functions**: Map new functionalities to TMDb API endpoints.
2. **Update AI Agent**: Integrate the new functions into the AI agent's capabilities.
3. **Test**: Ensure the new features work as expected and handle errors gracefully.

### Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **SignalWire**: For providing the AI Gateway and enabling seamless integration of AI functionalities into the SignalWire AI Agent.
- **OpenAI**: For the GPT models that power the natural language understanding and generation capabilities of the AI agent.
- **TMDb**: For the comprehensive movie database that provides up-to-date movie information.

## Contact

For questions or support, please contact [brian@signalwire.com](mailto:brian@signalwire.com).
