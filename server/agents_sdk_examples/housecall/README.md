# HouseCall

A sophisticated AI-powered voice agent for real estate that manages inbound inquiries through intelligent conversational flow handling lead capture, property searches, appointment scheduling, and agent transfers.

## Source Repository

The full source code is maintained in a separate repository:

**[github.com/signalwire-demos/housecall](https://github.com/signalwire-demos/housecall)**

## Features

- **Caller Identification** - Trestle reverse-phone lookup with 90-day caching
- **Lead Profiling** - 7-question collection including price range, property type, and timeline
- **Lead Scoring** - Automated scoring up to 100 points with auto-qualify at 60+
- **Property Search** - Filtering and sequential "speed tour" presentation
- **Appointment Scheduling** - Viewings and consultations with SMS confirmation
- **Agent Transfer** - Live agent transfer or callback scheduling
- **Web Dashboard** - CRUD for leads, appointments, call log, and properties

## Architecture

- **Backend**: Python (Starlette/ASGI) with SignalWire Agents SDK
- **Database**: SQLite with WAL mode
- **APIs**: Trestle (phone enrichment), Google Maps (optional)

## Getting Started

See the [main repository](https://github.com/signalwire-demos/housecall) for setup and deployment instructions.
