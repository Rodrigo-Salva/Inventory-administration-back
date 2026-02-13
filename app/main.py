from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.v1 import auth, products

app = FastAPI(title="Inventory SaaS", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])

@app.get("/")
async def root():
    return {"message": "Inventory SaaS - Multi-tenant listo!"}