"""Main FastAPI application for image resizing."""

import os
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
import asyncio
import hashlib
from contextlib import asynccontextmanager
import time
import concurrent.futures
import multiprocessing

from fastapi import FastAPI, HTTPException, Query, Depends, Request, Response as FastAPIResponse
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from PIL import Image
import aiofiles
import aiofiles.os
import io
import logging
from functools import lru_cache

from .cache import CacheManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("imgdude")

# Configuration
class Config:
    """Configuration for ImgDude. Values can be overridden by environment variables."""
    MEDIA_ROOT = os.environ.get("IMGDUDE_MEDIA_ROOT", "./media")
    CACHE_DIR = os.environ.get("IMGDUDE_CACHE_DIR", "./cache")
    CACHE_MAX_AGE = int(os.environ.get("IMGDUDE_CACHE_MAX_AGE", "604800"))
    MAX_WIDTH = int(os.environ.get("IMGDUDE_MAX_WIDTH", "2000"))
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    TRUSTED_HOSTS_PROVIDED = len(os.environ.get("IMGDUDE_TRUSTED_HOSTS", "").strip()) > 0
    TRUSTED_HOSTS = os.environ.get("IMGDUDE_TRUSTED_HOSTS", "*").split(",") if TRUSTED_HOSTS_PROVIDED else ["*"]
    ALLOWED_ORIGINS_PROVIDED = len(os.environ.get("IMGDUDE_ALLOWED_ORIGINS", "").strip()) > 0
    ALLOWED_ORIGINS = os.environ.get("IMGDUDE_ALLOWED_ORIGINS", "*").split(",") if ALLOWED_ORIGINS_PROVIDED else ["*"]
    CACHE_HEADERS = {
        "Cache-Control": f"public, max-age={CACHE_MAX_AGE}",
        "X-ImgDude-Cache": "HIT"
    }
    NO_CACHE_HEADERS = {
        "Cache-Control": "no-store, no-cache, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }
    CPU_COUNT = multiprocessing.cpu_count()
    IMAGE_PROCESSING_WORKERS = int(os.environ.get("IMGDUDE_IMAGE_WORKERS", str(max(2, CPU_COUNT - 1))))
    FILE_IO_WORKERS = int(os.environ.get("IMGDUDE_IO_WORKERS", str(max(2, CPU_COUNT // 2))))
    MAX_CONNECTIONS = int(os.environ.get("IMGDUDE_MAX_CONNECTIONS", "100"))

config = Config()

cache_manager = CacheManager(config.CACHE_DIR, config.CACHE_MAX_AGE)

image_processing_pool = None
file_io_pool = None

TESTING_MODE = False

if os.environ.get("IMGDUDE_TESTING_MODE", "").lower() in ("1", "true", "yes"):
    logger.warning("TESTING_MODE is enabled - security checks are bypassed! Never use this in production.")
    TESTING_MODE = True

class TrustedHostMiddleware(BaseHTTPMiddleware):
    """Restricts access to trusted hosts only."""
    async def dispatch(self, request: Request, call_next: Callable) -> FastAPIResponse:
        if TESTING_MODE or not config.TRUSTED_HOSTS_PROVIDED or "*" in config.TRUSTED_HOSTS:
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = f"{process_time:.4f} seconds"
            return response

        client_host = request.client.host if request.client else None
        if client_host not in config.TRUSTED_HOSTS:
            logger.warning(f"Blocked request from untrusted host: {client_host}")
            return Response(
                content=f"Access denied: {client_host} is not in trusted hosts list",
                status_code=403
            )
        
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.4f} seconds"
        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events for the application."""
    global image_processing_pool, file_io_pool
    
    image_processing_pool = concurrent.futures.ThreadPoolExecutor(
        max_workers=config.IMAGE_PROCESSING_WORKERS, 
        thread_name_prefix="img_proc"
    )
    
    file_io_pool = concurrent.futures.ThreadPoolExecutor(
        max_workers=config.FILE_IO_WORKERS, 
        thread_name_prefix="file_io"
    )
    
    os.makedirs(config.MEDIA_ROOT, exist_ok=True)
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    
    cleanup_task = asyncio.create_task(cache_manager.start_periodic_cleanup())
    
    logger.info(f"ImgDude started with:")
    logger.info(f"  MEDIA_ROOT: {config.MEDIA_ROOT}")
    logger.info(f"  CACHE_DIR: {config.CACHE_DIR}")
    logger.info(f"  TRUSTED_HOSTS: {config.TRUSTED_HOSTS}")
    logger.info(f"  ALLOWED_ORIGINS: {config.ALLOWED_ORIGINS}")
    logger.info(f"  IMAGE_PROCESSING_WORKERS: {config.IMAGE_PROCESSING_WORKERS}")
    logger.info(f"  FILE_IO_WORKERS: {config.FILE_IO_WORKERS}")
    logger.info(f"  MAX_CONNECTIONS: {config.MAX_CONNECTIONS}")
    
    try:
        yield
    finally:
        logger.info("Shutting down ImgDude")
        
        if cleanup_task:
            cleanup_task.cancel()
            try:
                await cleanup_task
            except asyncio.CancelledError:
                pass
        
        if image_processing_pool:
            image_processing_pool.shutdown(wait=True)
        if file_io_pool:
            file_io_pool.shutdown(wait=True)
        
        logger.info("ImgDude shutdown complete")

# Create app with middleware
app = FastAPI(
    title="ImgDude",
    description="Image resizing proxy standalone backend",
    version="1.0.1",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(TrustedHostMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "HEAD"],
    allow_headers=["*"],
)

def validate_path(filepath: str) -> Path:
    """Ensures the requested file path is safe and valid."""
    try:
        requested_path = Path(filepath)
        
        normalized_path = Path(os.path.normpath(filepath))
        if ".." in normalized_path.parts or normalized_path.is_absolute():
            logger.warning(f"Path traversal attempt detected: {filepath}")
            raise HTTPException(status_code=403, detail="Path traversal detected")
        
        if requested_path.suffix.lower() not in config.ALLOWED_EXTENSIONS:
            logger.warning(f"Unsupported file extension: {requested_path.suffix}")
            raise HTTPException(status_code=400, detail="Unsupported file extension")
        
        abs_path = Path(config.MEDIA_ROOT) / requested_path
        
        try:
            abs_path.relative_to(Path(config.MEDIA_ROOT))
        except ValueError:
            logger.warning(f"Invalid path attempt: {filepath}")
            raise HTTPException(status_code=403, detail="Invalid path")
        
        return abs_path
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Path validation error: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid file path")

@lru_cache(maxsize=1000)
def get_cache_path(filepath: Path, width: Optional[int]) -> Path:
    """Generates a unique cache path for a resized image."""
    original_path = str(filepath.relative_to(config.MEDIA_ROOT) if filepath.is_absolute() else filepath)
    cache_key = f"{original_path}_w{width}"
    hashed = hashlib.md5(cache_key.encode()).hexdigest()
    
    return Path(config.CACHE_DIR) / f"{hashed}{filepath.suffix}"

@lru_cache(maxsize=100)
def get_mime_type(file_extension: str) -> str:
    """Returns the mime type for a given file extension."""
    extension_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return extension_map.get(file_extension.lower(), "application/octet-stream")

async def resize_image(img_data: bytes, width: int) -> bytes:
    """Resizes an image to the specified width, keeping the aspect ratio."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(image_processing_pool, _resize_image_sync, img_data, width)

async def read_file_async(file_path: Path) -> bytes:
    """Reads a file asynchronously using the file I/O thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(file_io_pool, _read_file_sync, file_path)

async def write_file_async(file_path: Path, data: bytes) -> None:
    """Writes a file asynchronously using the file I/O thread pool."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(file_io_pool, _write_file_sync, file_path, data)

def _read_file_sync(file_path: Path) -> bytes:
    """Synchronous version of read_file to run in a thread pool."""
    with open(file_path, "rb") as f:
        return f.read()

def _write_file_sync(file_path: Path, data: bytes) -> None:
    """Synchronous version of write_file to run in a thread pool."""
    os.makedirs(file_path.parent, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(data)

def _resize_image_sync(img_data: bytes, width: int) -> bytes:
    """Synchronous version of resize_image to run in a thread pool."""
    try:
        start_time = time.time()
        img = Image.open(io.BytesIO(img_data))
        
        if img.width <= width:
            logger.debug(f"Image already at or below requested width ({img.width} <= {width})")
            return img_data
        
        ratio = width / float(img.width)
        height = int(ratio * img.height)
        
        img = img.resize((width, height), Image.LANCZOS)
        
        buffer = io.BytesIO()
        format_to_use = img.format if img.format else 'JPEG'
        
        save_options = {}
        if format_to_use in ('JPEG', 'PNG'):
            save_options['optimize'] = True
        
        if format_to_use == 'JPEG' and img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
            
        img.save(buffer, format=format_to_use, **save_options)
        
        process_time = time.time() - start_time
        logger.debug(f"Image resized in {process_time:.4f} seconds")
        
        return buffer.getvalue()
    except Exception as e:
        logger.error(f"Image resize error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error resizing image")

connection_semaphore = asyncio.Semaphore(config.MAX_CONNECTIONS)

@app.get("/image/{filepath:path}")
async def get_image(filepath: str, w: Optional[int] = Query(None, ge=1, le=config.MAX_WIDTH)):
    """Serve an image, optionally resizing it."""
    async with connection_semaphore:
        try:
            start_time = time.time()
            
            abs_path = validate_path(filepath)
            
            if not os.path.exists(abs_path):
                logger.warning(f"Image not found: {abs_path}")
                raise HTTPException(status_code=404, detail="Image not found")
            
            headers = {}
            
            if w is None:
                image_data = await read_file_async(abs_path)
                
                logger.debug(f"Serving original image: {filepath}")
                return Response(
                    content=image_data,
                    media_type=get_mime_type(abs_path.suffix),
                    headers=headers
                )
            
            cache_path = get_cache_path(abs_path, w)
            if os.path.exists(cache_path):
                cached_data = await read_file_async(cache_path)
                
                cache_manager.mark_accessed(str(cache_path))
                
                process_time = time.time() - start_time
                logger.debug(f"Cache hit for {filepath} (w={w}), served in {process_time:.4f} seconds")
                
                headers.update(config.CACHE_HEADERS)
                
                return Response(
                    content=cached_data,
                    media_type=get_mime_type(abs_path.suffix),
                    headers=headers
                )
            
            image_data = await read_file_async(abs_path)
            
            resized_data = await resize_image(image_data, w)
            
            await write_file_async(cache_path, resized_data)
            
            process_time = time.time() - start_time
            logger.debug(f"Cache miss for {filepath} (w={w}), processed in {process_time:.4f} seconds")
            
            headers.update({
                "Cache-Control": f"public, max-age={config.CACHE_MAX_AGE}",
                "X-ImgDude-Cache": "MISS"
            })
            
            return Response(
                content=resized_data,
                media_type=get_mime_type(abs_path.suffix),
                headers=headers
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/cache/stats")
async def cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    return await cache_manager.get_cache_stats()

@app.post("/cache/clean")
async def clean_cache() -> Dict[str, Any]:
    """Manually clean the cache."""
    result = await cache_manager.clean_cache()
    return result

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    from . import __version__
    return {
        "status": "healthy", 
        "version": __version__,
        "trusted_hosts": config.TRUSTED_HOSTS,
        "allowed_origins": config.ALLOWED_ORIGINS,
        "default_port": 12312,
        "workers": {
            "image_processing": config.IMAGE_PROCESSING_WORKERS,
            "file_io": config.FILE_IO_WORKERS,
            "max_connections": config.MAX_CONNECTIONS
        }
    } 