import requests
from django.conf import settings
from django.utils import timezone

class DeviceBackendService:
    """Service for communicating with the device backend"""

    def __init__(self):
        # Get these from settings (or fallback)
        self.api_base_url = getattr(
            settings,
            'DEVICE_BACKEND_URL',
            'http://10.10.4.230:8000/central/register'
        )
        self.api_token = getattr(settings, 'DEVICE_BACKEND_TOKEN', '')

    def _get_headers(self):
        return {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
        }

    def verify_device(self, device_id, ip_address, port, configuration=None):
        """
        Send a verification request to the device backend with configuration.
        Returns (success, message)
        """
        try:
            data = {
                'device_id': device_id,
                'ip_address': ip_address,
                'port': port,
                'timestamp': timezone.now().isoformat(),
            }
            if configuration:
                data['configuration'] = configuration

            response = requests.post(
                f'{self.api_base_url}/api/devices/verify/',
                headers=self._get_headers(),
                json=data,
                timeout=5
            )
            if response.status_code == 200:
                payload = response.json()
                return True, payload.get('message', 'Device verified successfully')
            return False, f"Backend returned error: {response.status_code} - {response.text}"
        except Exception as e:
            return False, f"Communication error: {str(e)}"

    def send_device_configuration(self, device_id, configuration, token=None):
        """Send device configuration to the backend"""
        try:
            headers = self._get_headers()
            if token:
                headers['Device-Token'] = token

            response = requests.post(
                f'{self.api_base_url}/api/devices/{device_id}/configuration/',
                headers=headers,
                json=configuration,
                timeout=5
            )
            if response.status_code in (200, 201):
                payload = response.json()
                return True, payload.get('message', 'Configuration sent successfully')
            return False, f"Backend returned error: {response.status_code} - {response.text}"
        except Exception as e:
            return False, f"Communication error: {str(e)}"

    def check_device_status(self, device_id):
        """Check the current status of a device with the backend"""
        try:
            response = requests.get(
                f'{self.api_base_url}/api/devices/{device_id}/status/',
                headers=self._get_headers(),
                timeout=5
            )
            if response.status_code == 200:
                payload = response.json()
                return payload.get('online', False), payload.get('status', 'Unknown')
            return False, f"Backend returned error: {response.status_code}"
        except Exception as e:
            return False, f"Communication error: {str(e)}"

    def get_device_token(self, device_id):
        """Retrieve authentication token for a device from the backend"""
        try:
            response = requests.get(
                f'{self.api_base_url}/api/devices/{device_id}/token/',
                headers=self._get_headers(),
                timeout=5
            )
            if response.status_code == 200:
                payload = response.json()
                return True, payload.get('token', '')
            return False, f"Backend returned error: {response.status_code} - {response.text}"
        except Exception as e:
            return False, f"Communication error: {str(e)}"

    def register_device(self, device_id, status_report):
        """
        Send a registration + status report to the central backend.
        Returns (success, payload_or_error).
        """
        url = f"{self.api_base_url}/central/register"
        headers = {
            "Content-type": "application/json",
            "X-Kiosk-Token": self.api_token
        }
        try:
            resp = requests.post(
                url,
                headers=headers,
                json={"status_report": status_report},
                timeout=5
            )
            if resp.status_code == 200:
                return True, resp.json()
            return False, f"Error {resp.status_code}: {resp.text}"
        except Exception as e:
            return False, f"Communication error: {str(e)}"