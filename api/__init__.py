"""FastAPI surface over core/. Shared by the Gradio app and the HTML frontend."""

from api.routes import router

__all__ = ["router"]
