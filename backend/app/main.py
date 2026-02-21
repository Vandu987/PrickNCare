from fastapi import FastAPI

app = FastAPI(
    title="PricknCare API",
    description="PAN India Phlebotomist Blood Sample Collection Platform",
    version="0.1.0",
)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}
