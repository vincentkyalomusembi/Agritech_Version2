from app.integrations.google_earth_engine.ndvi import NDVIService


def main():

    service = NDVIService()

    result = service.get_ndvi(
        latitude=0.0463,      # Meru
        longitude=37.6559,
    )

    print(result)


if __name__ == "__main__":
    main()