"""Minimal SWAIG function tests for Bobby's Table."""
import requests
import json

BASE_URL = "http://localhost:8080"

# Basic health check
resp = requests.get(f"{BASE_URL}/swaig")
print("/swaig", resp.status_code)

# Try listing reservations via SWAIG (if running)
try:
    data = {"function": "get_reservation", "params": {"format": "json"}}
    resp = requests.post(f"{BASE_URL}/receptionist", json=data)
    print("/receptionist", resp.status_code)
    print(json.dumps(resp.json(), indent=2))
except Exception as e:
    print("Error calling SWAIG function:", e)

