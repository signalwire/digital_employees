# Zen Cable Customer Portal

A modern customer portal for cable service management, featuring real-time modem status monitoring, service management, and appointment scheduling.

## Features

- 🔐 Secure authentication system
- 📱 Real-time modem status monitoring
- 💳 Online bill payment
- 📅 Appointment scheduling
- 📊 Service management
- 🤖 SignalWire SWAIG integration for voice interactions

## Prerequisites

- Python 3.10 or higher
- SQLite3
- ngrok (for local development with SignalWire)
- SignalWire account (for voice integration)

## Run on Replit

Click the button below to import and run this project on Replit:

[![Run on Replit](https://replit.com/badge?theme=dark&variant=small)](https://replit.com/new/github/Len-PGH/zen_python)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd zen_python
   ```

2. Create and activate a virtual environment:
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   # Copy the example env file
   cp .env.example .env
   
   # Edit .env with your actual values
   ```

## Configuration

Create a `.env` file with the following variables:

```env
# Flask Configuration
HOST=0.0.0.0
PORT=5000
FLASK_ENV=development

# SignalWire Configuration
SIGNALWIRE_PROJECT_ID=your_project_id
SIGNALWIRE_TOKEN=your_token
SIGNALWIRE_SPACE=your_space
```

## Running the Application

### Local Development

1. Initialize the database:
   ```bash
   python init_db.py
   python init_test_data.py
   ```

2. Start the Flask application:
   ```bash
   python app.py
   ```

3. For SignalWire integration, start ngrok:
   ```bash
   ngrok http 5000
   ```

### Replit Deployment

1. Import the project into Replit
2. Configure the run command in `.replit`:
   ```toml
   run = "python app.py"
   ```
3. Set up environment variables in Replit's Secrets tab:
   - `HOST`: `0.0.0.0`
   - `PORT`: `8080`
   - `FLASK_ENV`: `development`
   - `SIGNALWIRE_PROJECT_ID`: Your SignalWire project ID
   - `SIGNALWIRE_TOKEN`: Your SignalWire token
   - `SIGNALWIRE_SPACE`: Your SignalWire space

4. Initialize the database:
   ```bash
   # In Replit shell
   python init_db.py
   python init_test_data.py
   ```

5. Click the "Run" button or use the shell:
   ```bash
   python app.py
   ```

The app will be available at your Replit URL (e.g., `https://your-repl-name.your-username.repl.co`)

## Usage

### Test Account

Use these credentials to test the application:
- Email: `test@example.com`
- Password: `password123`

### Modem Management

- View real-time modem status
- Reboot modem remotely
- Monitor connection quality

### Service Management

- View active services
- Check billing status
- Make payments
- Schedule appointments

### Voice Integration

The SignalWire SWAIG integration supports:
- Balance checking
- Payment processing
- Modem status monitoring
- Appointment scheduling
- Modem swap requests

## Development

### Project Structure

```
zen_python/
├── app.py              # Main application file
├── init_db.py          # Database initialization
├── init_test_data.py   # Test data population
├── requirements.txt    # Python dependencies
├── static/            # Static files (CSS, JS)
├── templates/         # HTML templates
└── zen_cable.db       # SQLite database
```

### Database Schema

The application uses SQLite with the following main tables:
- `customers`: Customer information
- `services`: Available services
- `customer_services`: Customer subscriptions
- `modems`: Modem information
- `appointments`: Service appointments
- `billing`: Billing information
- `payments`: Payment records

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Security

- Passwords are hashed using SHA-256 with salt
- Session management with secure cookies
- CSRF protection
- SQL injection prevention
- XSS protection

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the repository or contact the development team. 