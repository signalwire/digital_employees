# MovieBot - SignalWire AI Agent for Movie Information

MovieBot is an AI-powered agent built with the SignalWire AI Agents SDK that provides movie information, recommendations, and answers questions about films using The Movie Database (TMDB) API.

## Features

- Movie search and detailed information
- Actor and director information
- Trending and upcoming movie recommendations
- Theater listings (what's playing now)
- Genre-based movie discovery
- Personalized movie recommendations

## Setup

### Prerequisites

- Python 3.7 or higher
- SignalWire AI Agents SDK
- TMDB API key (get one at [https://www.themoviedb.org/settings/api](https://www.themoviedb.org/settings/api))

### Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/moviebot.git
cd moviebot
```

2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

3. Set up your TMDB API key:

```bash
export TMDB_API_KEY=your_api_key_here
```

## Running the MovieBot

Start the MovieBot agent:

```bash
python moviebot.py
```

This will start the agent on the default host (0.0.0.0) and port (3000). You can customize these settings:

```bash
python moviebot.py --host 127.0.0.1 --port 8000
```

Once running, the agent will display its URL and basic authentication credentials.

## Integration with SignalWire

To connect the MovieBot to a SignalWire phone number:

1. Log in to your SignalWire dashboard
2. Navigate to Phone Numbers → Manage
3. Select a number or purchase a new one
4. Under "When a call comes in," set the Request URL to your MovieBot's URL (e.g., http://your-server:3000/moviebot)
5. Set the HTTP Authentication Username and Password to match the displayed values
6. Save your settings

Now, when someone calls your SignalWire number, they'll be connected to the MovieBot agent!

## How it Works

The MovieBot leverages:

1. **SignalWire AI Agents SDK**: Provides the foundation for building conversational AI agents
2. **OpenAI LLM**: Powers the natural language understanding via SignalWire
3. **TMDB API**: Provides up-to-date movie information

The agent is configured with:
- A personality that makes it knowledgeable about movies
- SWAIG functions that allow it to fetch real-time movie data
- Prompt sections that guide its behavior and knowledge

## Example Conversations

- "What movies are trending this week?"
- "Tell me about the movie Inception"
- "Who starred in The Shawshank Redemption?"
- "What's playing in theaters right now?"
- "Recommend some science fiction movies from 2023"
- "Tell me about director Christopher Nolan"

## Credits

- This project uses the [SignalWire AI Agents SDK](https://github.com/signalwire/signalwire-ai-agents)
- Movie data is provided by [The Movie Database (TMDB)](https://www.themoviedb.org/)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Thanks to SignalWire for the AI Agents SDK
- Thanks to TMDB for their comprehensive movie API
