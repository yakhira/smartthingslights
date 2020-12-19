"""Platform for SmartThingsLights integration."""
import logging
import re
import requests
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from datetime import timedelta
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from homeassistant.components.light import PLATFORM_SCHEMA, LightEntity

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=5)
ST_API_URL = 'https://api.smartthings.com/v1'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required('token'): cv.string,
    vol.Optional('exclude'): vol.All(cv.ensure_list, [cv.string])
})

def st_connect(token, exclude=[]):
    http_adapter = HTTPAdapter(
        max_retries=Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 501, 502, 503, 504]
        )
    )

    session = requests.Session()
    session.mount('http://', http_adapter)
    session.mount('https://', http_adapter)
    session.devices = {}
    session.token = token

    if token:
        response = session.get(
            f'{ST_API_URL}/devices?capability=switch',
            headers={
                'Authorization': f'Bearer {token}'
            }
        )
        if response.status_code == 200:
            session.devices = [
                {
                    'id': device['deviceId'],
                    'name': device['label']
                } 
                for device in response.json()['items']
                if device['label'] not in exclude
            ]
    return session

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the SmartThingsLights."""
    token = config['token'].replace('Bearer ', '')
    exclude = config.get('exclude', [])
    session = st_connect(token, exclude)

    add_entities([
        SmartThingsLights(device, session)
        for device in session.devices
    ])

class SmartThingsLights(LightEntity):
    """Representation of an SmartThingsLights."""

    def __init__(self, device, session):
        """Initialize an SmartThingsLights."""
        self._name = device['name']
        self._device_id = device['id']
        self._session = session
        self._state = None

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state
    
    def get_light_state(self):
        response = self._session.get(
            f"{ST_API_URL}/devices/{self._device_id}/status",
            headers={
                'Authorization': f'Bearer {self._session.token}'
            }
        )
        if response.status_code == 200:
            for key, value in response.json()['components']['main']['switch'].items():
                return value.get('value')
        return False
    
    def set_light_state(self, state):
        response = self._session.post(
            f"{ST_API_URL}/devices/{self._device_id}/commands",
            headers={
                'Authorization': f'Bearer {self._session.token}'
            },
            json= {
                'commands': [
                    {
                        'component': 'main',
                        'capability': 'switch',
                        'command': state
                    }
                ]
            }
        )
        if response.status_code == 200:
            return True
        return False

    def turn_on(self, **kwargs):
        """Instruct the light to turn on."""
        self.set_light_state('on')

    def turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        self.set_light_state('off')

    def update(self):
        """Fetch new state data for this light.
        This is the only method that should fetch new data for Home Assistant.
        """
        light_state = self.get_light_state()

        if light_state == 'on':
            self._state = True
        elif light_state == 'off':
            self._state = False

        return self._state