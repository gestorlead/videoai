#!/usr/bin/env python3
"""
Teste rápido para verificar se FastAPI está funcionando
"""

from fastapi import FastAPI
import uvicorn

app = FastAPI(
    title="VideoAI API",
    description="AI Video Creation & Social Media Platform",
    version="1.0.0-alpha"
)

@app.get("/")
async def root():
    return {
        "message": "VideoAI API is running!",
        "status": "success",
        "version": "1.0.0-alpha"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "videoai-api"
    }

if __name__ == "__main__":
    print("🎬 Starting VideoAI FastAPI test...")
    uvicorn.run(app, host="0.0.0.0", port=8000) 