# GoAir

A voice-powered flight booking system where an AI agent named "Voyager" enables callers to search flights, compare options, confirm pricing, book trips, and receive SMS confirmations entirely through natural voice conversation.

## Source Repository

The full source code is maintained in a separate repository:

**[github.com/signalwire-demos/goair](https://github.com/signalwire-demos/goair)**

## Features

- **Returning Passenger Recognition** - Caller ID lookup with pre-filled preferences
- **Passenger Profiles** - 8-field collection including seat/cabin preference and home airport
- **Airport Resolution** - Disambiguation via Google Maps Geocoding
- **Flight Search** - Round-trip and one-way support with 150+ airports and 28 airlines
- **Smart Pricing** - Distance-based with cabin multipliers and time-of-day adjustments
- **Route-Aware Airlines** - Hub carriers preferred for realistic results
- **Booking Confirmation** - PNR generation with SMS confirmation
- **Web Dashboard** - Booking stats, revenue, and filterable table

## Architecture

- **Backend**: Python with SignalWire Agents SDK
- **APIs**: Google Maps Geocoding, Mock Amadeus-compatible flight API
- **Database**: SQLite (call state, bookings, passengers)

## Getting Started

See the [main repository](https://github.com/signalwire-demos/goair) for setup and deployment instructions.
