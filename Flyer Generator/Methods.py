import requests
from PIL import Image
from io import BytesIO
import os
from bs4 import BeautifulSoup
from pathlib import Path
import zipfile

def download_image(url):
        """Saves an image from a URL to a local file"""

        try:
            # Download the image
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # Raise an HTTPError for bad responses

            # Open the image
            img = Image.open(BytesIO(response.content))

        except requests.exceptions.RequestException as e:
            print(f"Network error while fetching {url}: {e}")

        except UnidentifiedImageError:
            print(f"The content at {url} is not a valid image.")

        except OSError as e:
            print(f"Error saving or processing the image: {e}")

        return img



def save_image(img, filename):
    print("Attempting to save image at filepath:")
    print(filename)
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        img.save(filename)
    except:
        print("Error saving image.")
    
    return Path(filename).resolve()

def get_featured_media(post):
    """
    Given a WordPress post object (from the REST API),
    return the full media object for the featured image,
    or None if not found.
    Works for WordPress.com (no _embed) and self-hosted sites.
    """
    # Case 1: Try _embedded (self-hosted with ?_embed=1)
    if "_embedded" in post and "wp:featuredmedia" in post["_embedded"]:
        try:
            return post["_embedded"]["wp:featuredmedia"][0]
        except (KeyError, IndexError):
            pass

    # Case 2: Use _links -> wp:featuredmedia (WordPress.com style)
    if "_links" in post and "wp:featuredmedia" in post["_links"]:
        try:
            media_url = post["_links"]["wp:featuredmedia"][0]["href"]
            media = requests.get(media_url).json()
            return media
        except Exception:
            pass

def clean_text(text):
    # Remove any HTML gunk
    soup = BeautifulSoup(text, features = "html.parser")
    text = soup.get_text(separator=' ', strip=True)

    # Common 'smart' characters in unicode that break our simpleminded latin-1 strings
    text = text.replace('\u2019', "'")  # right single quote (apostrophe)
    text = text.replace('\u2018', "'")  # left single quote  
    text = text.replace('\u201c', '"')  # left double quote â€œ
    text = text.replace('\u201d', '"')  # right double quote
    text = text.replace('\u2013', '–')  # en dash
    text = text.replace('\u2014', '—')  # em dash â€
    text = text.replace('\u2026', '...')  # ellipsis

    print("Text cleaned.")
    return text

class ZipBuilder:
    def __init__(self):
        self.buffer = io.BytesIO()
        self.zipf = zipfile.ZipFile(self.buffer, 'w')
        self.closed = False
    
    def add_image(self, image, location, filename=None):
        if self.closed:
            raise ValueError("ZipBuilder is already closed")
        
        # Your zip_image logic here
        if filename is None:
            format_name = getattr(image, 'format', 'PNG') or 'PNG'
            ext = 'jpg' if format_name == 'JPEG' else format_name.lower()
            filename = f"image_{len(self.zipf.namelist()) + 1}.{ext}"
        
        if location and not location.endswith('/'):
            location += '/'
        
        zip_path = f"{location}{filename}" if location else filename
        
        img_bytes = io.BytesIO()
        image.save(img_bytes, format=getattr(image, 'format', None) or 'PNG')
        self.zipf.writestr(zip_path, img_bytes.getvalue())
        return self  # Allow chaining!
    
    def add_text(self, content, filename):
        if self.closed:
            raise ValueError("ZipBuilder is already closed")
        self.zipf.writestr(filename, content.encode('utf-8'))
        return self
    
    def getvalue(self):
        if not self.closed:
            self.zipf.close()
            self.closed = True
        return self.buffer.getvalue()