# Veronica

A SignalWire voice AI agent that collects and validates email addresses and physical addresses from inbound callers. All routing logic lives in code — the LLM only handles personality and natural language.

## Source Repository

The full source code is maintained in a separate repository:

**[github.com/signalwire-demos/veronica](https://github.com/signalwire-demos/veronica)**

## Features

- **Deterministic Routing** - State machine drives all flow; AI never decides routing
- **Pre-Call Enrichment** - Trestle reverse phone, Google Maps, and Smarty US Street API
- **Email Collection** - Voice spelling with up to 3 retry attempts
- **Email Validation** - ZeroBounce real-time validation mid-call
- **Confirmation Email** - Postmark delivery on verbal consent
- **Address Validation** - Two-stage: Google Maps geocoding + Smarty USPS CASS/DPV
- **Consent Tracking** - All consent logged with phone, call_id, type, and timestamp
- **Returning Callers** - Cached enrichment data with zero repeat API calls

## Architecture

- **Backend**: Python with SignalWire Agents SDK
- **APIs**: Trestle, ZeroBounce, Postmark, Google Maps, Smarty US Street
- **Database**: SQLite (callers, call_state, consent_log)

## Getting Started

See the [main repository](https://github.com/signalwire-demos/veronica) for setup and deployment instructions.
