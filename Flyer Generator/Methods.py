import requests
from PIL import Image
from io import BytesIO
import io
import os
from bs4 import BeautifulSoup
from pathlib import Path
import zipfile
import csv

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
    """Removes certain bad unicode characters and removes HTML gunk"""
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
    """
    A convenient class for building zip files in memory.
    Handles the ZipFile object lifecycle automatically.
    """
    
    def __init__(self):
        """Initialize a new ZipBuilder with an empty zip in memory."""
        self.buffer = io.BytesIO()
        self.zipf = zipfile.ZipFile(self.buffer, 'w', zipfile.ZIP_DEFLATED)
        self.closed = False
    
    def verify_zip(self):
        """Ensure the zip file is still open for writing."""
        if self.closed:
            raise ValueError("ZipBuilder is already closed. Cannot add more content.")
        if self.zipf is None or self.zipf.fp is None:
            raise ValueError("ZipBuilder's internal zipfile is not available.")
    
    def _normalize_path(self, location, filename):
        """Create a normalized path within the zip file."""
        if location and not location.endswith('/'):
            location += '/'
        return f"{location}{filename}" if location else filename
    
    def add_image(self, image, location='', filename=None, image_format=None):
        """
        Add a PIL Image to the zip file.
        
        Args:
            image: PIL Image object
            location: Directory path within zip (e.g., 'photos/', 'images/2024/')
            filename: Optional filename. If None, generates automatically
            image_format: Optional format override. If None, uses image's format or PNG
        
        Returns:
            self: For method chaining
        """
        self.verify_zip()
        
        # Determine image format
        if image_format is None:
            image_format = getattr(image, 'format', None) or 'PNG'
        
        # Generate filename if not provided
        if filename is None:
            extension = image_format.lower()
            if extension == 'jpeg':
                extension = 'jpg'
            filename = f"image_{len(self.zipf.namelist()) + 1}.{extension}"
        
        # Create full path in zip
        zip_path = self._normalize_path(location, filename)
        
        # Convert image to bytes
        img_bytes = io.BytesIO()
        image.save(img_bytes, format=image_format)
        
        # Add to zip
        self.zipf.writestr(zip_path, img_bytes.getvalue())
        
        return self
    
    def add_text(self, content, filename, location='', encoding='utf-8'):
        """
        Add text content to the zip file.
        
        Args:
            content: String content to add
            filename: Name of the file in the zip
            location: Directory path within zip
            encoding: Text encoding (default: utf-8)
        
        Returns:
            self: For method chaining
        """
        self.verify_zip()
        
        zip_path = self._normalize_path(location, filename)
        self.zipf.writestr(zip_path, content.encode(encoding))
        
        return self
    
    def add_csv(self, rows, filename, location='', encoding='utf-8'):
        """
        Add CSV data to the zip file.
        
        Args:
            rows: List of lists/tuples representing CSV rows
            filename: Name of the CSV file in the zip
            location: Directory path within zip
            encoding: Text encoding (default: utf-8)
        
        Returns:
            self: For method chaining
        """
        self.verify_zip()
        
        # Create CSV content
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerows(rows)
        
        # Add to zip
        zip_path = self._normalize_path(location, filename)
        self.zipf.writestr(zip_path, csv_buffer.getvalue().encode(encoding))
        
        return self
    
    def add_bytes(self, data, filename, location=''):
        """
        Add raw bytes to the zip file.
        
        Args:
            data: Bytes to add
            filename: Name of the file in the zip
            location: Directory path within zip
        
        Returns:
            self: For method chaining
        """
        self.verify_zip()
        
        zip_path = self._normalize_path(location, filename)
        self.zipf.writestr(zip_path, data)
        
        return self
    
    def add_file(self, file_path, zip_filename=None, location=''):
        """
        Add a file from disk to the zip.
        
        Args:
            file_path: Path to the file on disk
            zip_filename: Name in the zip (if None, uses original filename)
            location: Directory path within zip
        
        Returns:
            self: For method chaining
        """
        self.verify_zip()
        
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if zip_filename is None:
            zip_filename = file_path.name
        
        zip_path = self._normalize_path(location, zip_filename)
        self.zipf.write(str(file_path), zip_path)
        
        return self
    
    def list_contents(self):
        """
        Get a list of all files currently in the zip.
        
        Returns:
            list: List of filenames in the zip
        """
        return self.zipf.namelist()
    
    def get_info(self):
        """
        Get information about the current zip contents.
        
        Returns:
            dict: Information about the zip file
        """
        files = self.zipf.namelist()
        return {
            'file_count': len(files),
            'files': files,
            'is_closed': self.closed,
            'approximate_size_bytes': len(self.buffer.getvalue())
        }
    
    def getvalue(self):
        """
        Get the complete zip file as bytes. This closes the zip file.
        
        Returns:
            bytes: Complete zip file data
        """
        if not self.closed:
            self.zipf.close()
            self.closed = True
        
        return self.buffer.getvalue()
    
    def save_to_file(self, filepath):
        """
        Save the zip to a file on disk.
        
        Args:
            filepath: Path where to save the zip file
        """
        zip_bytes = self.getvalue()
        with open(filepath, 'wb') as f:
            f.write(zip_bytes)
    
    def __len__(self):
        """Return the number of files in the zip."""
        return len(self.zipf.namelist())
    
    def __enter__(self):
        """Support for context manager (with statement)."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Automatically close when exiting context manager."""
        if not self.closed:
            self.zipf.close()
            self.closed = True