#!/usr/bin/env python3
"""
Startup script for Bobby's Table Restaurant
Runs the integrated Flask web application with SignalWire agents
"""

import os
import sys

def main():
    """Main function to start the integrated service"""
    print("🍽️  Starting Bobby's Table Restaurant System")
    print("=" * 50)
    print("🌐 Web Interface: http://localhost:8080")
    print("📞 Voice Interface: http://localhost:8080/receptionist")
    print("🍳 Kitchen Dashboard: http://localhost:8080/kitchen")
    print("\nPress Ctrl+C to stop the service")
    print("-" * 50)

    try:
        # Import and run the Flask app with integrated SWAIG agents
        from app import app, cleanup_payment_sessions_on_startup, start_payment_session_cleanup_scheduler
        
        # Clean up any orphaned payment sessions from previous runs
        cleanup_payment_sessions_on_startup()
        
        # Start automatic cleanup scheduler
        start_payment_session_cleanup_scheduler()
        
        app.run(host="0.0.0.0", port=8080, debug=True)

    except KeyboardInterrupt:
        print("\n🛑 Shutting down service...")
        print("✅ Service stopped")
    except Exception as e:
        print(f"❌ Error starting service: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
