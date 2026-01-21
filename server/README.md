# Server Examples

Server-side examples for building SignalWire digital employees with backend integrations.

## Directory Structure

### Agents SDK Examples (`agents_sdk_examples/`)

Examples using the [SignalWire Agents SDK](https://github.com/signalwire/signalwire-agents) - a Python framework for building AI-powered digital employees with skills-based architecture.

| Example | Description |
|---------|-------------|
| [bobbys_table](agents_sdk_examples/bobbys_table/) | Restaurant reservation system with Stripe payments and kitchen dashboard |
| [fresh_valley_market](agents_sdk_examples/fresh_valley_market/) | Grocery store digital employee |
| [sigmond_blackjack](agents_sdk_examples/sigmond_blackjack/) | Video blackjack game with AI dealer ([external repo](https://github.com/signalwire-demos/blackjack)) |
| [sigmond_holyguacamole](agents_sdk_examples/sigmond_holyguacamole/) | Voice-controlled drive-thru ordering system ([external repo](https://github.com/signalwire-demos/holy-guacamole)) |
| [cinebot](agents_sdk_examples/cinebot/) | AI-powered movie discovery assistant ([external repo](https://github.com/signalwire-demos/cinebot)) |
| [santa](agents_sdk_examples/santa/) | AI Santa with video conversations ([external repo](https://github.com/signalwire-demos/santa)) |
| [afterhours](agents_sdk_examples/afterhours/) | After-hours HVAC emergency service ([external repo](https://github.com/signalwire-demos/afterhours)) |
| [example](agents_sdk_examples/example/) | Starter template for AI agents ([external repo](https://github.com/signalwire-demos/example)) |

### SWAIG Examples

Examples using SWAIG (SignalWire AI Gateway) with various backend languages.

#### Python (`python_examples/`)

| Example | Description |
|---------|-------------|
| [moviebot](python_examples/moviebot/) | Movie expert AI agent using TMDb API |
| [dental_office](python_examples/dental_office/) | Click-to-call with MFA, calendar, and appointments |
| [bobbystable](python_examples/bobbystable/) | Restaurant reservation system (legacy) |
| [zen_cable](python_examples/zen_cable/) | Cable company Tier 1 support |

#### Perl (`perl_examples/`)

| Example | Description |
|---------|-------------|
| [bobbys_table](perl_examples/bobbys_table/) | Restaurant reservation with MFA |
| [flos_flowers](perl_examples/flos_flowers/) | SMS e-card flower delivery |
| [ai_calendar](perl_examples/ai_calendar/) | Google Calendar integration |
| [roomie_serve](perl_examples/roomie_serve/) | Hotel/hospital room service |
| [zen](perl_examples/zen/) | Cable modem Tier 1 support |
| [mfa](perl_examples/mfa/) | Multi-factor authentication reference |
| [babelfish](perl_examples/babelfish/) | Translation and language bot |

#### Node.js (`node_examples/`)

| Example | Description |
|---------|-------------|
| [ai_calendar_demo](node_examples/ai_calendar_demo/) | Google Calendar integration |

### Tools (`tools/`)

| Tool | Description |
|------|-------------|
| [tap](tools/tap/) | RTP audio stream listener |

## Getting Started

Each example contains its own README with setup instructions. Generally:

1. Navigate to the example directory
2. Install dependencies (see `requirements.txt`, `package.json`, or `cpanfile`)
3. Configure environment variables (see `.env.example` if available)
4. Run the application

## SignalWire SDKs

- **Agents SDK**: High-level Python framework with skills-based architecture
- **SWAIG**: SignalWire AI Gateway for webhook-based integrations in any language
