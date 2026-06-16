"""BilimAI - Web versiya (FastAPI backend).

Ishga tushirish:
    uvicorn web:app --reload
yoki:
    python web.py
Keyin brauzerda oching: http://localhost:8000
"""

import logging

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from bilim_ai import ai, config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BilimAI.web")

app = FastAPI(title="BilimAI", description="O'quv yordamchisi", version="1.0.0")


@app.get("/api/health")
async def health():
    """Server holatini tekshirish."""
    return {
        "status": "ok",
        "configured": config.is_configured(),
        "provider": config.active_provider() or None,
    }


@app.post("/api/chat")
async def chat(message: str = Form(...)):
    """Matnli savolga javob."""
    import asyncio

    if not config.is_configured():
        return JSONResponse(
            status_code=503,
            content={
                "error": "AI kaliti sozlanmagan. .env faylga GEMINI_API_KEY yoki "
                "GROQ_API_KEY qo'shing."
            },
        )
    try:
        answer = await asyncio.to_thread(ai.ask, message)
        return {"answer": answer, "provider": config.active_provider()}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Chat xatosi")
        return JSONResponse(status_code=500, content={"error": str(exc)})


@app.post("/api/chat-image")
async def chat_image(
    image: UploadFile = File(...),
    message: str = Form(""),
):
    """Rasm + (ixtiyoriy) matn bilan savol."""
    import asyncio

    try:
        data = await image.read()
        mime = image.content_type or "image/jpeg"
        answer = await asyncio.to_thread(ai.ask_with_image, data, mime, message)
        return {"answer": answer, "provider": "gemini"}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Rasm chat xatosi")
        return JSONResponse(status_code=500, content={"error": str(exc)})


# Statik fayllar (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web:app", host="0.0.0.0", port=config.PORT, reload=False)
