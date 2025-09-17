import requests
from PIL import Image
from io import BytesIO
import os
from pathlib import Path

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