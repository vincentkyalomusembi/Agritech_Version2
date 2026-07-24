from app.integrations.google_earth_engine.service import (
    EarthEngineService,
)


def main():

    service = EarthEngineService()

    result = service.get_environment(
        latitude=0.0463,
        longitude=37.6559,
    )

    print(result)


if __name__ == "__main__":
    main()