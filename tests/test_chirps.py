from app.integrations.google_earth_engine.chirps import CHIRPSService


def main():
    service = CHIRPSService()

    result = service.get_rainfall(
        latitude=0.0463,
        longitude=37.6559,  #Meru, Kenya
    )

    print(result)


if __name__ == "__main__":
    main()