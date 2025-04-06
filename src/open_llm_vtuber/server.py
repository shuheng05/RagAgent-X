import os
import shutil
import httpx

from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response

from .routes import init_client_ws_route, init_webtool_routes
from .service_context import ServiceContext
from .config_manager.utils import Config


class CustomStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if path.endswith(".js"):
            response.headers["Content-Type"] = "application/javascript"
        return response


class AvatarStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        allowed_extensions = (".jpg", ".jpeg", ".png", ".gif", ".svg")
        if not any(path.lower().endswith(ext) for ext in allowed_extensions):
            return Response("Forbidden file type", status_code=403)
        return await super().get_response(path, scope)


class WebSocketServer:
    def __init__(self, config: Config):
        self.app = FastAPI()

        # Add CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Load configurations and initialize the default context cache
        default_context_cache = ServiceContext()
        default_context_cache.load_from_config(config)

        # Include routes
        self.app.include_router(
            init_client_ws_route(default_context_cache=default_context_cache),
        )
        self.app.include_router(
            init_webtool_routes(default_context_cache=default_context_cache),
        )

        # Mount cache directory
        if not os.path.exists("cache"):
            os.makedirs("cache")
        self.app.mount(
            "/cache",
            StaticFiles(directory="cache"),
            name="cache",
        )

        # Reverse proxy: /api -> Flask, /voice -> GPT-SoVITS
        @self.app.api_route("/api/{path:path}", methods=["GET", "POST"])
        async def proxy_api(request: Request, path: str):
            target_url = f"http://127.0.0.1:5000/{path}"  # Flask 的服务地址
            async with httpx.AsyncClient() as client:
                headers = dict(request.headers)
                if request.method == "POST":
                    body = await request.body()
                    response = await client.post(target_url, content=body, headers=headers)
                else:
                    response = await client.get(target_url, params=dict(request.query_params), headers=headers)
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response.headers
            )

        @self.app.api_route("/voice/{path:path}", methods=["GET", "POST"])
        async def proxy_voice(request: Request, path: str):
            target_url = f"http://127.0.0.1:9885/{path}"  # GPT-SoVITS 的地址
            async with httpx.AsyncClient() as client:
                headers = dict(request.headers)
                if request.method == "POST":
                    body = await request.body()
                    response = await client.post(target_url, content=body, headers=headers)
                else:
                    response = await client.get(target_url, params=dict(request.query_params), headers=headers)
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response.headers
            )

        # Mount static files
        self.app.mount(
            "/live2d-models",
            StaticFiles(directory="live2d-models"),
            name="live2d-models",
        )
        self.app.mount(
            "/bg",
            StaticFiles(directory="backgrounds"),
            name="backgrounds",
        )
        self.app.mount(
            "/avatars",
            AvatarStaticFiles(directory="avatars"),
            name="avatars",
        )

        # Mount web tool
        self.app.mount(
            "/web-tool",
            CustomStaticFiles(directory="web_tool", html=True),
            name="web_tool",
        )

        # Mount main frontend
        self.app.mount(
            "/",
            CustomStaticFiles(directory="frontend", html=True),
            name="frontend",
        )

    def run(self):
        pass

    @staticmethod
    def clean_cache():
        """Clean the cache directory by removing and recreating it."""
        cache_dir = "cache"
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
        os.makedirs(cache_dir)
