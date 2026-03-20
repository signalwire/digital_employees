# Gino's Pizza

An AI-powered pizza ordering system featuring voice interaction combined with a real-time visual pizza builder that stacks transparent PNG layers as customers make selections.

## Source Repository

The full source code is maintained in a separate repository:

**[github.com/signalwire-demos/ginospizza](https://github.com/signalwire-demos/ginospizza)**

## Features

- **Visual Pizza Builder** - Transparent PNG layers stack in real-time as toppings are added
- **Voice Ordering** - 14-step conversation flow with 30 SWAIG tools
- **Multiple Pizzas** - Order multiple pizzas with size-proportional display rendering
- **Specialty Presets** - 5 preset options including Meat Lover's and Hawaiian
- **Topping Variety** - 12 topping varieties with variable amounts and placement
- **On-Screen Menu** - Highlights the current build step
- **Sides Ordering** - Order sides without a pizza

## Architecture

- **Backend**: Python with Flask/Uvicorn
- **Voice**: WebRTC for voice communication
- **Frontend**: Vanilla JavaScript and CSS
- **Assets**: 1024x1024 transparent PNG layers organized by ingredient

## Getting Started

See the [main repository](https://github.com/signalwire-demos/ginospizza) for setup and deployment instructions.
