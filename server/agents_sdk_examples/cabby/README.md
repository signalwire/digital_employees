# Cabby

A voice-powered AI taxi booking system where callers interact with an AI dispatcher to handle ride bookings, rebooking prior trips, cancellations, address updates, and SMS confirmations.

## Source Repository

The full source code is maintained in a separate repository:

**[github.com/signalwire-demos/cabby](https://github.com/signalwire-demos/cabby)**

## Features

- **Caller Recognition** - Returning caller detection with pre-loaded profiles
- **Ride Booking** - Google Places address validation and Google Routes fare calculation
- **Quick Rebook** - Rebook last trip or reverse trip (swap pickup/destination)
- **Saved Addresses** - Save home/work addresses for future convenience
- **Fare Calculation** - Distance-based formula with base rate, mileage, and time components
- **SMS Confirmations** - Booking confirmations and cancellation notices
- **Web Dashboard** - Real-time booking data with auto-refresh

## Architecture

- **Backend**: Python with SignalWire Agents SDK
- **APIs**: Google Places (address validation), Google Routes (fare calculation)
- **Database**: SQLite (customers, trips)

## Getting Started

See the [main repository](https://github.com/signalwire-demos/cabby) for setup and deployment instructions.
