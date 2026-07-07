from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.farmers.exceptions import (
    FarmerNotFoundError,
    PhoneNumberAlreadyExistsError,
    NationalIDAlreadyExistsError,
    InvalidPinError,
    InactiveFarmerError,
)


def register_exception_handlers(app: FastAPI):
    
    #Register all custom exception handlers.
    

    @app.exception_handler(FarmerNotFoundError)
    async def farmer_not_found_handler(
        request: Request,
        exc: FarmerNotFoundError,
    ):
        return JSONResponse(
            status_code=404,
            content={
                "detail": str(exc),
            },
        )

    @app.exception_handler(PhoneNumberAlreadyExistsError)
    async def phone_exists_handler(
        request: Request,
        exc: PhoneNumberAlreadyExistsError,
    ):
        return JSONResponse(
            status_code=409,
            content={
                "detail": str(exc),
            },
        )

    @app.exception_handler(NationalIDAlreadyExistsError)
    async def national_id_exists_handler(
        request: Request,
        exc: NationalIDAlreadyExistsError,
    ):
        return JSONResponse(
            status_code=409,
            content={
                "detail": str(exc),
            },
        )

    @app.exception_handler(InvalidPinError)
    async def invalid_pin_handler(
        request: Request,
        exc: InvalidPinError,
    ):
        return JSONResponse(
            status_code=401,
            content={
                "detail": str(exc),
            },
        )

    @app.exception_handler(InactiveFarmerError)
    async def inactive_farmer_handler(
        request: Request,
        exc: InactiveFarmerError,
    ):
        return JSONResponse(
            status_code=403,
            content={
                "detail": str(exc),
            },
        )