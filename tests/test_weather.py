from app.integrations.openweather.client import (
    OpenWeatherClient,
)


def main():

    client = OpenWeatherClient()

    result = client.get_weather(
        latitude=0.0463,
        longitude=37.6559,
    )

    print(result)


if __name__ == "__main__":
    main()