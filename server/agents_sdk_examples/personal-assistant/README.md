# Personal Assistant

A comprehensive voice AI assistant named "Ethan" built on SignalWire Agents SDK that handles inbound business calls with appointment scheduling, email/calendar integration, FAQ search, and message taking.

## Source Repository

The full source code is maintained in a separate repository:

**[github.com/signalwire-demos/personal-assistant](https://github.com/signalwire-demos/personal-assistant)**

## Features

- **Appointment Management** - Booking, cancellation, and checking via Google Calendar
- **Business Info** - Hours, location, services, and pricing
- **FAQ Search** - AI-powered search and RAG-based knowledge base queries
- **Message Taking** - Collect messages from callers
- **Call Transfer** - Transfer to business owner
- **Owner Mode** - Gmail management, message review, calendar management, contact lookup
- **Multi-Tenant** - Support for multiple businesses
- **Document Upload** - AI indexing for knowledge base
- **Web Dashboard** - Admin configuration interface

## Architecture

- **Backend**: Python (FastAPI) with SQLAlchemy ORM
- **APIs**: Google Gmail, Calendar, People (via OAuth)
- **Deployment**: Docker, Heroku, Railway, Render, Fly.io, AWS, GCP, Azure

## Getting Started

See the [main repository](https://github.com/signalwire-demos/personal-assistant) for setup and deployment instructions.
