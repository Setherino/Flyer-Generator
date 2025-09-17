import requests
import json
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from urllib.parse import urljoin
import qrcode
from PIL import Image
import io
from io import BytesIO
import os
from pathlib import Path

def save_image(url, filename):
        """Saves an image from a URL to a local file"""

        try:
            # Download the image
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # Raise an HTTPError for bad responses

            # Open the image
            img = Image.open(BytesIO(response.content))
    
            # Save image
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            img.save(filename)

        except requests.exceptions.RequestException as e:
            print(f"Network error while fetching {url}: {e}")

        except UnidentifiedImageError:
            print(f"The content at {url} is not a valid image.")

        except OSError as e:
            print(f"Error saving or processing the image: {e}")

        return Path(filename).resolve()
