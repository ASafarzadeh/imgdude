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
- `--workers INTEGER`: Number of worker processes for the server. (Default: Number of CPU cores; Env: `IMGDUDE_WORKERS`)
- `--threads INTEGER`: Number of threads per worker. (Default: `1`; Env: `IMGDUDE_THREADS`)
- `--log-level TEXT`: Logging level (e.g., `critical`, `error`, `warning`, `info`, `debug`, `trace`). (Default: `info`; Env: `IMGDUDE_LOG_LEVEL`)
- `--access-log / --no-access-log`: Enable/disable access log. (Default: Enabled; Env: `IMGDUDE_ACCESS_LOG`)
- `--use-colors / --no-use-colors`: Enable/disable colored logging. (Default: Enabled if TTY; Env: `IMGDUDE_USE_COLORS`)
- `--env-file PATH`: Load environment variables from a file.
- `--cleanup-interval INTEGER`: Interval in seconds for periodic cache cleanup. (Default: `3600`; Env: `IMGDUDE_CLEANUP_INTERVAL_SECONDS`)
- `--image-processing-workers INTEGER`: Number of workers for the image processing thread pool. (Default: Number of CPU cores; Env: `IMGDUDE_IMAGE_PROCESSING_WORKERS`)
- `--file-io-workers INTEGER`: Number of workers for the file I/O thread pool. (Default: `10`; Env: `IMGDUDE_FILE_IO_WORKERS`)
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

- `--workers INTEGER`: Number of worker processes for the server. (Default: Number of CPU cores; Env: `IMGDUDE_WORKERS`)
- `--threads INTEGER`: Number of threads per worker. (Default: `1`; Env: `IMGDUDE_THREADS`)
- `--log-level TEXT`: Logging level (e.g., `critical`, `error`, `warning`, `info`, `debug`, `trace`). (Default: `info`; Env: `IMGDUDE_LOG_LEVEL`)
- `--access-log / --no-access-log`: Enable/disable access log. (Default: Enabled; Env: `IMGDUDE_ACCESS_LOG`)
- `--use-colors / --no-use-colors`: Enable/disable colored logging. (Default: Enabled if TTY; Env: `IMGDUDE_USE_COLORS`)
- `--env-file PATH`: Load environment variables from a file.
- `--cleanup-interval INTEGER`: Interval in seconds for periodic cache cleanup. (Default: `3600`; Env: `IMGDUDE_CLEANUP_INTERVAL_SECONDS`)
- `--image-processing-workers INTEGER`: Number of workers for the image processing thread pool. (Default: Number of CPU cores; Env: `IMGDUDE_IMAGE_PROCESSING_WORKERS`)
- `--file-io-workers INTEGER`: Number of workers for the file I/O thread pool. (Default: `10`; Env: `IMGDUDE_FILE_IO_WORKERS`)

**Key Environment Variables:**

- `IMGDUDE_MEDIA_ROOT`: Path to the directory containing original images.
- `IMGDUDE_CACHE_DIR`: Path to the directory where resized images will be cached.
- `IMGDUDE_TRUSTED_HOSTS`: Comma-separated list of allowed host headers. (Default: `*`)
- `IMGDUDE_CACHE_MAX_AGE_SECONDS`: Maximum age for cached files in seconds. (Default: `604800` (7 days))
- `IMGDUDE_CACHE_MAX_SIZE_MB`: Maximum total size for the image cache in megabytes. (Default: `1024`)
- `IMGDUDE_LOG_LEVEL`: Logging level (e.g., `INFO`, `DEBUG`). (Default: `INFO`)
- `IMGDUDE_DEFAULT_IMAGE_QUALITY`: Default quality for resized JPEG/WebP images (1-100). (Default: `85`)
- `IMGDUDE_MAX_RESIZE_WIDTH`: Maximum allowed width for image resizing. (Default: `4000`)
- `IMGDUDE_MAX_RESIZE_HEIGHT`: Maximum allowed height for image resizing. (Default: `4000`)
- `IMGDUDE_WORKERS`: Number of worker processes for the server.
- `IMGDUDE_THREADS`: Number of threads per worker.
- `IMGDUDE_ACCESS_LOG`: Set to `true` or `false` to enable/disable access log.
- `IMGDUDE_USE_COLORS`: Set to `true` or `false` to enable/disable colored logging.
- `IMGDUDE_CLEANUP_INTERVAL_SECONDS`: Interval in seconds for periodic cache cleanup.
- `IMGDUDE_IMAGE_PROCESSING_WORKERS`: Number of workers for the image processing thread pool.
- `IMGDUDE_FILE_IO_WORKERS`: Number of workers for the file I/O thread pool.

## API Usage

ImgDude exposes a primary endpoint for image resizing:

`GET /image/{image_path}`

Where `{image_path}` is the relative path to the image within your `IMGDUDE_MEDIA_ROOT`.

**Query Parameters:**

- `w` (integer, optional): Target width in pixels. If only `w` or `h` is provided, aspect ratio is maintained.
- `h` (integer, optional): Target height in pixels.
- `q` (integer, optional): Output quality for JPEG or WebP formats (1-100). (Default: `85`)
- `format` (string, optional): Desired output image format (e.g., `jpeg`, `png`, `webp`). If omitted, ImgDude attempts to use the original format or a sensible default.

**Example:**

To resize `myfolder/myimage.jpg` to a width of 300 pixels with 80% quality:

`/image/myfolder/myimage.jpg?w=300&q=80`

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
