import os
import httpx
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, validator

app = FastAPI(title="API Gateway", version="1.0.0")

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:5001")
DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://data-service:5002")


class LoginRequest(BaseModel):
    username: str
    password: str

    @validator("username")
    def username_not_empty(cls, v):
        if not v.strip():
            raise ValueError("username must not be blank")
        return v.strip()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/auth/login")
async def login(req: LoginRequest):
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{AUTH_SERVICE_URL}/login",
            json={"username": req.username, "password": req.password},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json())
    return resp.json()


@app.post("/data/items", status_code=201)
async def create_item(
    payload: dict,
    authorization: str = Header(default=None),
):
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{DATA_SERVICE_URL}/items",
            json=payload,
            headers={"Authorization": authorization or ""},
        )
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@app.get("/data/items")
async def list_items(authorization: str = Header(default=None)):
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{DATA_SERVICE_URL}/items",
            headers={"Authorization": authorization or ""},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@app.post("/data/notify")
async def notify(
    payload: dict,
    authorization: str = Header(default=None),
):
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{DATA_SERVICE_URL}/notify",
            json=payload,
            headers={"Authorization": authorization or ""},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()
