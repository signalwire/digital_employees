# Santa

[![Try it](https://img.shields.io/badge/🎅_Try_Now-santa.signalwire.io-green?style=for-the-badge)](https://santa.signalwire.io)

An AI-powered Santa character that users can interact with through WebRTC video conversations. Features gift search capabilities and automated deployment infrastructure.

## Source Repository

The full source code is maintained in a separate repository:

**[github.com/signalwire-demos/santa](https://github.com/signalwire-demos/santa)**

## Features

- **Video Conversations** - WebRTC-based video calls with AI Santa
- **Gift Search** - Integrated gift recommendations via RapidAPI
- **Auto Deployment** - GitHub → Dokku CI/CD pipeline
- **Preview Environments** - Unique URLs for pull request previews
- **SSL Management** - Automatic Let's Encrypt certificates
- **Zero-Downtime Deploys** - Seamless updates

## Architecture

- **Backend**: Python with FastAPI (uvicorn)
- **Frontend**: HTML, CSS, JavaScript
- **Communication**: WebRTC for video calls
- **APIs**: SignalWire AI, RapidAPI for gift search
- **Infrastructure**: Dokku containerized deployments

## Getting Started

See the [main repository](https://github.com/signalwire-demos/santa) for setup and deployment instructions.
