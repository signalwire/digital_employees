# Sigmond Holy Guacamole

A production-ready voice-controlled drive-thru ordering system demonstrating a **code-driven LLM architecture** where application logic controls the AI agent rather than the reverse.


<p align="center">
    <img src="https://github.com/user-attachments/assets/6b201001-6c10-4a84-a884-e7e0f56a36bc" alt="image" width="50%" />

</p>

## Source Repository

The full source code is maintained in a separate repository:

**[github.com/signalwire/sigmond-holyguacamole](https://github.com/signalwire/sigmond-holyguacamole)**

## Features

- **Voice-first interface** with WebRTC audio/video streaming
- **Real-time order visualization** showing items, quantities, and pricing
- **Intelligent menu matching** using multiple algorithms (TF-IDF, fuzzy matching, aliases)
- **Automatic combo detection** suggesting upgrades without LLM intervention
- **State machine architecture** enforcing conversation flow (greeting → taking order → confirming → complete)

## Architecture

The "code-driven" pattern embeds validation, pricing calculations, and business rules directly in functions rather than trusting the LLM to remember them. This ensures consistent, predictable behavior.

- **Backend**: Python with SignalWire Agents SDK
- **Frontend**: SignalWire Fabric SDK with HTML/JavaScript client
- **AI Tools**: SWAIG functions (add_item, remove_item, etc.)
- **Menu Matching**: scikit-learn TF-IDF vectorization + fuzzy matching
- **Communication**: WebRTC for real-time media streaming

## Key Innovation

This project showcases how to build conversational AI that's reliable, maintainable, and deterministic by having application logic control the AI agent rather than relying solely on prompt engineering.

## Getting Started

See the [main repository](https://github.com/signalwire/sigmond-holyguacamole) for setup and deployment instructions.
