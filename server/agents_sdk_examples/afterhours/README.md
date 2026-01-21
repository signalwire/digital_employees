# Afterhours (Wire Heating and Air)

An after-hours emergency HVAC service system that uses AI to handle incoming calls. The intelligent agent collects customer information and creates service requests visible on a real-time dashboard.

## Source Repository

The full source code is maintained in a separate repository:

**[github.com/signalwire-demos/afterhours](https://github.com/signalwire-demos/afterhours)**

## Features

- **24/7 Emergency Handling** - Automated call processing outside business hours
- **Smart Triage** - Classifies issues as emergency or routine
- **Guided Data Collection** - Gathers name, address, unit details, ownership status, callback number
- **Real-Time Dashboard** - Staff view incoming requests as they're submitted
- **Multi-Context AI** - Context-aware conversation flows to minimize errors

## Architecture

- **Backend**: Python with FastAPI and SignalWire Agents SDK
- **Frontend**: Vanilla JavaScript with SignalWire WebRTC SDK
- **AI Layer**: SWML with context-aware conversation management
- **Storage**: In-memory (no database required)
- **Deployment**: Dokku/Heroku compatible, ngrok for local development

## Getting Started

See the [main repository](https://github.com/signalwire-demos/afterhours) for setup and deployment instructions.
