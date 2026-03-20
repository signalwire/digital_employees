# Dental Office

A voice-powered dental office receptionist built on SignalWire AI Agents and the OpenDental API that handles inbound patient calls and proactive outbound calls.

## Source Repository

The full source code is maintained in a separate repository:

**[github.com/signalwire-demos/dental](https://github.com/signalwire-demos/dental)**

## Features

- **Caller Recognition** - Phone number lookup with DOB identity verification
- **New Patient Onboarding** - Collects name, DOB, phone, and email
- **Appointment Management** - Booking, confirmation, rescheduling, and cancellation
- **Insurance Management** - Full 5-step API chain for carrier, plan, subscription, and verification
- **Outbound Calls** - Appointment confirmations and recall reminders via APScheduler
- **Mock Mode** - Pre-seeded SQLite data for offline development
- **Dashboard API** - View calls, confirmations, and recalls

## Architecture

- **Backend**: Python with SignalWire Agents SDK
- **API**: OpenDental API (with mock mode)
- **Database**: SQLite state store
- **Scheduling**: APScheduler for outbound calls

## Getting Started

See the [main repository](https://github.com/signalwire-demos/dental) for setup and deployment instructions.
