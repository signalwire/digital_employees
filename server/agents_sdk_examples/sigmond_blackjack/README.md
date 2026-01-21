# Sigmond Blackjack

A fully functional blackjack game demonstrating how to build sophisticated SignalWire AI agents. Players connect via video call to an AI dealer, place bets, and play hands of blackjack with real-time UI updates.

<p align="center">
    <img src="https://github.com/user-attachments/assets/8d21a1c9-079e-4bde-abe4-5b235c38de33" alt="image" width="50%" />
  </p>




## Live Demo

[![Try it](https://img.shields.io/badge/🎮_Play_Now-blackjack.signalwire.me-green?style=for-the-badge)](https://blackjack.signalwire.me)

## Source Repository

The full source code is maintained in a separate repository:

**[github.com/signalwire-demos/blackjack](https://github.com/signalwire-demos/blackjack)**

## Features

- WebRTC video/audio integration for immersive gameplay
- AI dealer powered by Claude with ElevenLabs voice (Adam)
- Real-time web client communication through SWML user events
- Stateless game logic with state persistence via `global_data`
- Standard casino blackjack rules
- Chip management (starting with 1000 chips)
- Step-based conversation flow (betting → playing → hand_complete)

## Architecture

The application uses a **single-service architecture** where the AI agent simultaneously serves both the SWML API and web client from one process:

- **Backend**: Python with SignalWire Agents SDK
- **Frontend**: Vanilla JavaScript with SignalWire SDK
- **Communication**: WebRTC for video calls, event-driven architecture for game updates
- **Deployment**: Heroku/Dokku compatible via Procfile

## Getting Started

See the [main repository](https://github.com/signalwire-demos/blackjack) for setup and deployment instructions.
