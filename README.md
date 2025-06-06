# ImgDude

[![PyPI version](https://badge.fury.io/py/imgdude.svg)](https://badge.fury.io/py/imgdude)
[![Python Version](https://img.shields.io/pypi/pyversions/imgdude.svg)](https://pypi.org/project/imgdude/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

ImgDude is a high-performance image resizing proxy, built with FastAPI, designed for on-the-fly image processing and optimized delivery. It setups easily in a few minutes and features an efficient caching system.

## Key Features

- **On-the-fly Image Resizing:** Dynamically resize images via URL parameters, with automatic aspect ratio preservation.
- **Efficient Caching:** Built-in caching for resized images to minimize processing overhead and accelerate response times. Cache behavior (max age, max size) is configurable.
- **Easy Integration:** Designed for straightforward integration as a standalone image resizing backend, connecting easily with reverse proxies. An example Nginx configuration is provided.
- **High Performance:** Leverages FastAPI and asynchronous I/O to handle numerous concurrent requests efficiently.
- **Flexible Output Control:** Specify target dimensions (width, height), compression quality, and output image format (e.g., JPEG, PNG, WebP).
- **Configurable:** Customize application behavior using Command Line Interface (CLI) arguments or environment variables.

## Prerequisites

- Python 3.8+
- A reverse proxy (Like nginx)

## Installation

### From PyPI

```bash
pip install imgdude
```

### From Source

```bash
git clone https://github.com/ASafarzadeh/imgdude.git
cd imgdude
pip install .
# For development:
# pip install -e .[dev]
```

## Running ImgDude

ImgDude can be run directly from the command line or using Docker.

### Command Line

Start the ImgDude server using the `imgdude` command:

```bash
# Default configuration (host: 127.0.0.1, port: 12312)
imgdude

# Custom configuration
imgdude --host 0.0.0.0 --port 8080 --media-root /path/to/your/images --cache-dir /path/to/your/cache
```

**CLI Arguments:**

- `--host TEXT`: Server host. (Default: `127.0.0.1`)
- `--port INTEGER`: Server port. (Default: `12312`)
- `--media-root PATH`: Root directory for original image files. (Default: `./media`; Env: `IMGDUDE_MEDIA_ROOT`)
- `--cache-dir PATH`: Directory for storing cached resized images. (Default: `./cache`; Env: `IMGDUDE_CACHE_DIR`)
- `--cache-max-age INTEGER`: Maximum age for cached images in seconds. (Default: `604800` (7 days); Env: `IMGDUDE_CACHE_MAX_AGE`)
- `--max-width INTEGER`: Maximum allowed width for resized images. (Default: `2000`; Env: `IMGDUDE_MAX_WIDTH`)
- `--log-level TEXT`: Logging level (`debug`, `info`, `warning`, `error`, `critical`). (Default: `info`)
- `--trusted-hosts TEXT`: Comma-separated list of trusted host IPs. (Default: allow all hosts; Env: `IMGDUDE_TRUSTED_HOSTS`)
- `--allowed-origins TEXT`: Comma-separated list of allowed CORS origins. (Default: allow all origins; Env: `IMGDUDE_ALLOWED_ORIGINS`)
- `--image-workers INTEGER`: Number of worker threads for image processing. (Default: `max(2, CPU cores - 1)`; Env: `IMGDUDE_IMAGE_WORKERS`)
- `--io-workers INTEGER`: Number of worker threads for file I/O operations. (Default: `max(2, CPU cores / 2)`; Env: `IMGDUDE_IO_WORKERS`)
- `--max-connections INTEGER`: Maximum number of concurrent connections. (Default: `100`; Env: `IMGDUDE_MAX_CONNECTIONS`)
- `--workers INTEGER`: Number of Uvicorn worker processes for the server. (Default: `1`; Env: `IMGDUDE_WORKERS`)
- `--version`: Show version and exit.

### Docker

A `Dockerfile` and `docker-compose.yml` are provided for containerized deployment.

1.  **Update `docker-compose.yml`:** Modify the volume paths to point to your media and desired cache directories:

    ```yaml
    # docker-compose.yml (snippet)
    volumes:
      - /your/local/path/to/images:/app/media # Update this
      - /your/local/path/to/cache:/app/cache # Update this
    ```

2.  **Build and Run:**

    ```bash
    docker-compose up --build -d
    ```

    ImgDude will be accessible on the host at the port mapped in `docker-compose.yml` (default: `12312`).

## Configuration

ImgDude can be configured via CLI arguments (see above) or environment variables. Environment variables take precedence.

**Key CLI Arguments (beyond host/port/paths):**

- `--cache-max-age INTEGER`: Maximum age for cached images in seconds. (Default: `604800` (7 days); Env: `IMGDUDE_CACHE_MAX_AGE`)
- `--max-width INTEGER`: Maximum allowed width for resized images. (Default: `2000`; Env: `IMGDUDE_MAX_WIDTH`)
- `--log-level TEXT`: Logging level (`debug`, `info`, `warning`, `error`, `critical`). (Default: `info`)
- `--trusted-hosts TEXT`: Comma-separated list of trusted host IPs. (Default: allow all hosts; Env: `IMGDUDE_TRUSTED_HOSTS`)
- `--allowed-origins TEXT`: Comma-separated list of allowed CORS origins. (Default: allow all origins; Env: `IMGDUDE_ALLOWED_ORIGINS`)
- `--image-workers INTEGER`: Number of worker threads for image processing. (Default: `max(2, CPU cores - 1)`; Env: `IMGDUDE_IMAGE_WORKERS`)
- `--io-workers INTEGER`: Number of worker threads for file I/O operations. (Default: `max(2, CPU cores / 2)`; Env: `IMGDUDE_IO_WORKERS`)
- `--max-connections INTEGER`: Maximum number of concurrent connections. (Default: `100`; Env: `IMGDUDE_MAX_CONNECTIONS`)
- `--workers INTEGER`: Number of Uvicorn worker processes for the server. (Default: `1`; Env: `IMGDUDE_WORKERS`)

**Key Environment Variables:**

- `IMGDUDE_MEDIA_ROOT`: Path to the directory containing original images.
- `IMGDUDE_CACHE_DIR`: Path to the directory where resized images will be cached.
- `IMGDUDE_CACHE_MAX_AGE`: Maximum age for cached files in seconds. (Default: `604800` (7 days))
- `IMGDUDE_MAX_WIDTH`: Maximum allowed width for image resizing. (Default: `2000`)
- `IMGDUDE_TRUSTED_HOSTS`: Comma-separated list of trusted host IPs. (Default: allow all hosts)
- `IMGDUDE_ALLOWED_ORIGINS`: Comma-separated list of allowed CORS origins. (Default: allow all origins)
- `IMGDUDE_IMAGE_WORKERS`: Number of worker threads for image processing. (Default: `max(2, CPU cores - 1)`)
- `IMGDUDE_IO_WORKERS`: Number of worker threads for file I/O operations. (Default: `max(2, CPU cores / 2)`)
- `IMGDUDE_MAX_CONNECTIONS`: Maximum number of concurrent connections. (Default: `100`)
- `IMGDUDE_WORKERS`: Number of Uvicorn worker processes for the server. (Default: `1`)

## API Usage

ImgDude exposes a primary endpoint for image resizing:

`GET /image/{image_path}`

Where `{image_path}` is the relative path to the image within your `IMGDUDE_MEDIA_ROOT`.

**Query Parameters:**

- `w` (integer, optional): Target width in pixels. Aspect ratio is automatically maintained when resizing.

**Example:**

To resize `myfolder/myimage.jpg` to a width of 300 pixels:

`/image/myfolder/myimage.jpg?w=300`

## Nginx Integration

Here's an example Nginx configuration to proxy requests to ImgDude:

```nginx
# /etc/nginx/sites-available/your-site.conf

# Optional: Define a cache path for Nginx-level caching (distinct from ImgDude's cache)
proxy_cache_path /var/cache/nginx/imgdude levels=1:2 keys_zone=imgdude_cache:10m max_size=1g inactive=7d;

server {
    listen 80;
    server_name example.com; # Replace with your domain

    location ~ ^/media/([a-zA-Z0-9\-_./]+)\.(png|jpg|jpeg|gif|svg)$ {
        proxy_pass http://127.0.0.1:12312/image/$1.$2$is_args$args; # If you use like example.com/media/... for image links
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Use cache headers set by ImgDude
        proxy_cache_valid 200 7d;
        expires max;
        add_header Cache-Control "public, no-transform";
    }
    # Here you can add another location for /media, for fallbacks in case the format wasnt supported

}
```

This configuration uses a regex pattern to match image requests under `/media/` and passes them to the ImgDude service with proper query parameters.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
