import requests

from common.constants import HTTP_TIMEOUT, WEATHER_URL
from common.utils import require_env
from plugins import Plugin


class Weather(Plugin):
    name = 'weather'
    description = 'Get the current weather for a city.'
    parameters = {'city': 'city name'}
    required = ('city',)

    def run(self, city):
        params = {'q': city, 'appid': require_env('OPENWEATHER_API_KEY'), 'units': 'metric'}
        response = requests.get(WEATHER_URL, params=params, timeout=HTTP_TIMEOUT)
        if response.status_code == 404:
            return f"error: city not found: {city}"
        response.raise_for_status()
        data = response.json()
        return (f"{data['name']}: {data['main']['temp']:.1f}°C (feels like {data['main']['feels_like']:.1f}°C), "
                f"humidity {data['main']['humidity']}%, wind {data['wind']['speed']} m/s, "
                f"{data['weather'][0]['description']}")
