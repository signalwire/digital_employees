# Utility

A voice-powered customer service system for electric utilities (branded "Volt Electric") that enables customers to manage accounts through phone calls, featuring inbound service, outbound notifications, and a web dashboard.

## Source Repository

The full source code is maintained in a separate repository:

**[github.com/signalwire-demos/utility](https://github.com/signalwire-demos/utility)**

## Features

- **Bill Payment** - Credit card processing via DTMF input
- **Outage Reporting** - Report and check outage status by geographic zone
- **Service Requests** - Start, stop, and move service with address collection
- **Usage History** - 30-day daily breakdown
- **Customer Authentication** - 4-digit PIN verification
- **Outbound Notifications** - Proactive outage alerts and past-due payment reminders
- **Mock Mode** - 27 customers, 6 zones, 3 active outages, 3 months billing data
- **Web Dashboard** - Customer, outage, service request, and payment management

## Architecture

- **Backend**: Python (FastAPI) with SignalWire Agents SDK
- **Database**: SQLite state store + mock utility database
- **Scheduling**: APScheduler for outbound calls
- **Deployment**: AWS Lambda + API Gateway option available

## Getting Started

See the [main repository](https://github.com/signalwire-demos/utility) for setup and deployment instructions.
