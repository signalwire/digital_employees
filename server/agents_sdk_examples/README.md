# Agents SDK Examples

Examples built with the [SignalWire Agents SDK](https://github.com/signalwire/signalwire-agents) - a Python framework for building AI-powered digital employees.

## What is the Agents SDK?

The SignalWire Agents SDK provides a high-level, skills-based architecture for building conversational AI agents. Key features include:

- **Skills-based architecture** - Modular, reusable components for agent capabilities
- **State management** - Built-in persistence via `global_data` and `user_data`
- **Real-time events** - WebSocket and SWML user events for live updates
- **WebRTC integration** - Video and audio call support
- **Easy deployment** - Heroku/Dokku compatible

## Examples

| Example | Description |
|---------|-------------|
| [bobbys_table](bobbys_table/) | Restaurant reservation system with Stripe payments and kitchen dashboard |
| [fresh_valley_market](fresh_valley_market/) | Grocery store digital employee |
| [sigmond_blackjack](sigmond_blackjack/) | Video blackjack game with AI dealer ([external repo](https://github.com/signalwire/sigmond-blackjack)) |
| [sigmond_holyguacamole](sigmond_holyguacamole/) | Voice-controlled drive-thru ordering system ([external repo](https://github.com/signalwire/sigmond-holyguacamole)) |

## Getting Started

1. Install the SDK:
   ```bash
   pip install signalwire-agents
   ```

2. Navigate to an example directory

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables (see `.env.example` if available)

5. Run the application

## Documentation

- [Agents SDK Repository](https://github.com/signalwire/signalwire-agents)
- [SignalWire Documentation](https://developer.signalwire.com/)
