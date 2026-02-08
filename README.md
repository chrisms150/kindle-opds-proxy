<div align="center">

## Kindle OPDS Proxy

_A Flask-based proxy server that converts EPUB books from OPDS feeds to MOBI format for Kindle devices_

</div>

<div align="center">

![Python](https://img.shields.io/badge/python-3.11-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/flask-latest-black?style=for-the-badge&logo=flask)
![Docker](https://img.shields.io/badge/docker-ready-blue?style=for-the-badge&logo=docker)
![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)

</div>

---

## Important Compatibility Notes

- **This project has only been tested with [Booklore](https://www.booklore.app/) OPDS feeds**
- **Tested exclusively on Kindle devices from 2013**
- Compatibility with other OPDS providers or newer/older Kindle models is not guaranteed

## Features

- Browse OPDS catalogs through a web interface optimized for Kindle browsers
- Automatic EPUB to MOBI conversion using Calibre
- Cover image proxy support
- Authentication support for private OPDS feeds
- Mobile-responsive design for Kindle browsers

## Requirements

- Docker (recommended) or Python 3.11+
- Calibre (included in Docker image)
- Access to a Booklore OPDS feed

## Environment Variables

| Variable        | Description                      | Example                                    |
| --------------- | -------------------------------- | ------------------------------------------ |
| `OPDS_URL`      | Full URL to your OPDS feed       | `https://booklore.example.com/api/v1/opds` |
| `OPDS_USER`     | Username for OPDS authentication | `YourUsername`                             |
| `OPDS_PASSWORD` | Password for OPDS authentication | `YourPassword`                             |

## Quick Start with Docker Run

```bash
docker run -d \
  -p 5000:5000 \
  -e OPDS_URL="https://booklore.example.com/api/v1/opds" \
  -e OPDS_USER="YourUsername" \
  -e OPDS_PASSWORD="YourPassword" \
  --name kindle-opds-proxy \
  kindle-opds-proxy
```

Access the service at `http://localhost:5000` or `http://YOUR_SERVER_IP:5000`

## Docker Compose Example

Create a `docker-compose.yml` file:

```yaml
version: "3.8"

services:
  kindle-opds-proxy:
    build: .
    container_name: kindle-opds-proxy
    ports:
      - "5000:5000"
    environment:
      - OPDS_URL=https://booklore.example.com/api/v1/opds
      - OPDS_USER=YourUsername
      - OPDS_PASSWORD=YourPassword
    restart: unless-stopped
```

Run with:

```bash
docker-compose up -d
```

## Building the Docker Image

```bash
docker build -t kindle-opds-proxy .
```

## Usage

1. Start the service using either Docker run or Docker Compose
2. On your Kindle, open the experimental web browser
3. Navigate to `http://YOUR_SERVER_IP:5000`
4. Browse your OPDS catalog
5. Click on a book to view details
6. Click "Download" to get the book as a MOBI file
7. The book will automatically be added to your Kindle

## How It Works

1. The proxy fetches OPDS feeds from your Booklore server
2. Presents the catalog in a Kindle-friendly web interface
3. When you download a book:
   - Downloads the EPUB from the OPDS feed
   - Converts it to MOBI using Calibre's `ebook-convert`
   - Serves the MOBI file to your Kindle
   - Cleans up temporary files after 10 seconds

## Project Structure

```
kindle-opds-proxy/
├── server.py          # Main Flask application
├── requirements.txt   # Python dependencies
├── Dockerfile        # Docker build configuration
├── static/
│   └── style.css     # CSS for Kindle browser
├── cache/            # Temporary storage for conversions
└── README.md         # This file
```

## Manual Installation (Without Docker)

If you prefer to run without Docker:

1. Install Python 3.11+
2. Install Calibre and ensure `ebook-convert` is in your PATH
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set environment variables:
   ```bash
   export OPDS_URL="https://booklore.example.com/api/v1/opds"
   export OPDS_USER="YourUsername"
   export OPDS_PASSWORD="YourPassword"
   ```
5. Run the server:
   ```bash
   python server.py
   ```

## License

See [LICENSE](LICENSE) file for details.

## Contributing

This project is specifically tailored for Booklore OPDS feeds and 2013 Kindle devices. If you'd like to extend compatibility to other OPDS providers or Kindle models, contributions are welcome!

## Disclaimer

This is a hobby project tested in a specific environment. Use at your own risk.
