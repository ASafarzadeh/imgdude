"""Command line interface for imgdude."""

import os
import sys
import argparse
import logging
import uvicorn
import multiprocessing
from typing import NoReturn
from . import __version__

def main() -> None:
    """Entry point for running the ImgDude server."""
    cpu_count = multiprocessing.cpu_count()
    parser = argparse.ArgumentParser(
        description="ImgDude - Fast image resizing proxy standalone backend"
    )
    parser.add_argument(
        "--version", action="version", version=f"imgdude {__version__}"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind the server to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=12312, help="Port to bind the server to (default: 12312)"
    )
    parser.add_argument(
        "--media-root", 
        default=os.environ.get("IMGDUDE_MEDIA_ROOT", "./media"),
        help="Root directory for media files (default: ./media)"
    )
    parser.add_argument(
        "--cache-dir", 
        default=os.environ.get("IMGDUDE_CACHE_DIR", "./cache"),
        help="Directory for caching resized images (default: ./cache)"
    )
    parser.add_argument(
        "--cache-max-age", 
        type=int,
        default=int(os.environ.get("IMGDUDE_CACHE_MAX_AGE", "604800")),
        help="Maximum age for cached images in seconds (default: 604800, 7 days)"
    )
    parser.add_argument(
        "--max-width", 
        type=int,
        default=int(os.environ.get("IMGDUDE_MAX_WIDTH", "2000")),
        help="Maximum allowed width for resized images (default: 2000)"
    )
    parser.add_argument(
        "--log-level", 
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Logging level (default: info)"
    )
    parser.add_argument(
        "--trusted-hosts",
        default=os.environ.get("IMGDUDE_TRUSTED_HOSTS", ""),
        help="Comma-separated list of trusted host IPs (default: allow all hosts)"
    )
    parser.add_argument(
        "--allowed-origins",
        default=os.environ.get("IMGDUDE_ALLOWED_ORIGINS", ""),
        help="Comma-separated list of allowed CORS origins (default: allow all origins)"
    )
    parser.add_argument(
        "--image-workers",
        type=int,
        default=int(os.environ.get("IMGDUDE_IMAGE_WORKERS", str(max(2, cpu_count - 1)))),
        help=f"Number of worker threads for image processing (default: {max(2, cpu_count - 1)})"
    )
    parser.add_argument(
        "--io-workers",
        type=int,
        default=int(os.environ.get("IMGDUDE_IO_WORKERS", str(max(2, cpu_count // 2)))),
        help=f"Number of worker threads for file I/O operations (default: {max(2, cpu_count // 2)})"
    )
    parser.add_argument(
        "--max-connections",
        type=int,
        default=int(os.environ.get("IMGDUDE_MAX_CONNECTIONS", "100")),
        help="Maximum number of concurrent connections (default: 100)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.environ.get("IMGDUDE_WORKERS", "1")),
        help="Number of Uvicorn worker processes (default: 1)"
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    os.environ.update({
        "IMGDUDE_MEDIA_ROOT": args.media_root,
        "IMGDUDE_CACHE_DIR": args.cache_dir,
        "IMGDUDE_CACHE_MAX_AGE": str(args.cache_max_age),
        "IMGDUDE_MAX_WIDTH": str(args.max_width),
        "IMGDUDE_TRUSTED_HOSTS": args.trusted_hosts,
        "IMGDUDE_ALLOWED_ORIGINS": args.allowed_origins,
        "IMGDUDE_IMAGE_WORKERS": str(args.image_workers),
        "IMGDUDE_IO_WORKERS": str(args.io_workers),
        "IMGDUDE_MAX_CONNECTIONS": str(args.max_connections)
    })
    
    logger = logging.getLogger("imgdude.cli")
    logger.info(f"Starting ImgDude {__version__}")
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {args.port}")
    logger.info(f"Media Root: {args.media_root}")
    logger.info(f"Cache Directory: {args.cache_dir}")
    logger.info(f"Cache Max Age: {args.cache_max_age} seconds")
    logger.info(f"Max Width: {args.max_width} pixels")
    logger.info(f"Trusted hosts: {args.trusted_hosts if args.trusted_hosts else 'all hosts allowed'}")
    logger.info(f"Allowed origins: {args.allowed_origins if args.allowed_origins else 'all origins allowed'}")
    logger.info(f"Image Processing Workers: {args.image_workers}")
    logger.info(f"File I/O Workers: {args.io_workers}")
    logger.info(f"Max Connections: {args.max_connections}")
    logger.info(f"Uvicorn Workers: {args.workers}")
    try:
        os.makedirs(args.media_root, exist_ok=True)
        os.makedirs(args.cache_dir, exist_ok=True)
    except PermissionError:
        logger.error("Permission denied: Cannot create required directories")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to create directories: {e}")
        sys.exit(1)
    try:
        uvicorn.run(
            "imgdude.main:app", 
            host=args.host,
            port=args.port,
            log_level=args.log_level,
            workers=args.workers
        )
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 