import logging
import requests
import re
from signalwire.rest import Client as SignalWireClient

class SignalWireMFA:
    def __init__(self, project_id: str, token: str, space: str, from_number: str):
        try:
            # Handle both full URL and subdomain formats for space parameter
            if space.startswith('https://') or space.startswith('http://'):
                # Extract just the subdomain from full URL
                space_url = space
                if '://' in space:
                    space_subdomain = space.split('://')[1].split('.')[0]
                else:
                    space_subdomain = space.split('.')[0]
            else:
                # It's just a subdomain
                space_subdomain = space
                space_url = f"https://{space}.signalwire.com"
            
            # Initialize client with proper space URL format
            self.client = SignalWireClient(project_id, token, signalwire_space_url=f"{space_subdomain}.signalwire.com")
            self.project_id = project_id
            self.token = token
            self.space = space_subdomain
            self.from_number = from_number
            self.base_url = f"https://{space_subdomain}.signalwire.com/api/relay/rest"
            logging.debug(f"Initialized SignalWireMFA with from_number: {self.from_number}, space: {space_subdomain}")
        except Exception as e:
            logging.error(f"Failed to initialize SignalWire Client: {e}")
            raise

    def send_mfa(self, to_number: str) -> dict:
        try:
            url = f"{self.base_url}/mfa/sms"
            payload = {
                "to": to_number,
                "from": self.from_number,
                "message": "Here is your SignalWire Dental Office System code: ",
                "token_length": 6,
                "max_attempts": 3,
                "allow_alphas": False,
                "valid_for": 3600
            }
            headers = {"Content-Type": "application/json"}
            logging.debug(f"Sending MFA from {self.from_number} to {to_number}")
            response = requests.post(url, json=payload, auth=(self.project_id, self.token), headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error sending MFA: {e}")
            raise

    def verify_mfa(self, mfa_id: str, token: str) -> dict:
        try:
            verify_url = f"{self.base_url}/mfa/{mfa_id}/verify"
            payload = {"token": token}
            headers = {"Content-Type": "application/json"}
            logging.debug(f"Verifying MFA with ID {mfa_id} using token {token}")
            response = requests.post(verify_url, json=payload, auth=(self.project_id, self.token), headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            status_code = e.response.status_code
            if status_code == 401:
                return {"success": False, "message": "Unauthorized: Invalid credentials or MFA ID"}
            elif status_code == 400:
                return {"success": False, "message": "Bad Request: Invalid MFA code or parameters"}
            else:
                return {"success": False, "message": f"HTTP error {status_code}: {str(e)}"}
        except Exception as e:
            logging.error(f"Unexpected error verifying MFA: {e}")
            return {"success": False, "message": f"Unexpected error: {str(e)}"}

def is_valid_uuid(uuid_to_test, version=4):
    regex = {
        4: r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$'
    }
    pattern = regex.get(version)
    return bool(pattern and re.match(pattern, uuid_to_test))

def validate_phone(phone: str) -> bool:
    # Basic E.164 format validation
    pattern = r'^\+[1-9]\d{1,14}$'
    return bool(re.match(pattern, phone)) 