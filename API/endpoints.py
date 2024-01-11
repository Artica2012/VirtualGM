from fastapi import APIRouter


router = APIRouter()


@router.get("/", tags=["endpoints"])
async def root():
    return {"message": "Virtual GM"}


@router.get("/healthcheck", tags=["endpoints"])
def read_root():
    return {"status": "ok"}
