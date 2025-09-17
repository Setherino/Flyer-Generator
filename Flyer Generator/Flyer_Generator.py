from xml.etree.ElementTree import tostring
import Methods
import requests
import json
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from urllib.parse import urljoin
import qrcode
from PIL import Image
import io
import os
import re
import zipfile
import csv
from pathlib import Path

DEFAULT_IMG_SAVE_LOC = "Images/"
DEFAULT_CSV_SAVE_LOC = "CSV_FILES/"
DEFAULT_IMG_SAVE_ZIP = "Images/"
DEFAULT_CSV_SAVE_ZIP = "CSV_FILES/"


class Post:
    def __init__(self, post):
        """Initialize Post and fill variables from JSON"""

        with open("posts.json", "w", encoding="utf-8") as f:
            json.dump(post, f, ensure_ascii=False, indent=2)

        self.id = post.get('id')
        self.title = post.get('title', {}).get('rendered', '')
        self.exerpt = post.get('excerpt', {}).get('rendered', '')
        self.date = post.get('date')
        self.link = post.get('guid', {}).get('rendered', post.get('link', ''))
        self.author = post.get('author_meta',{}).get('display_name','')
        
        # Clean up the title, should not be any HTML but just to be sure:
        self.title =Methods.clean_text(self.title)
         

        #remove wordpress "smart" apostrophes, replace them with dumb ones.
        self.title = self.title.replace('\u2019', "'").replace('\u2018', "'")

        featured_media = Methods.get_featured_media(post)
        if featured_media:
            self.featured_image = {
                'url': featured_media.get('source_url'),
                'alt': featured_media.get('alt_text', ''),
                'caption': featured_media.get('caption', {}).get('rendered', '')
                }

        # Extract images from content using BeautifulSoup
        soup = BeautifulSoup(post['content']['rendered'], 'html.parser')
        img_tags = soup.find_all('img')
        self.images = [
            {
                'url': img.get('src', ''), 
                'alt': img.get('alt', ''),
                'title': img.get('title', ''),
                'width': img.get('width', ''),
                'height': img.get('height', '')
            } 
            for img in img_tags if img.get('src') # Filter broken <img> tags
            ]

        # Clean HTML from content for plain text (also using BeautifulSoup)
        self.body = soup.get_text(separator=' ', strip=True)

        self.body = Methods.clean_text(self.body)

    def generate_qr_code(self, size=10, border=4):
        """Generate QR code from the post URL"""
        qr = qrcode.QRCode(
            version=1,  # Controls size (1 is smallest)
            error_correction=qrcode.constants.ERROR_CORRECT_L,  # Low error correction
            box_size=size,  # Size of each box in pixels
            border=border,  # Border size in boxes
        )
        
        qr.add_data(self.link)
        qr.make(fit=True)
        
        # Create image
        self.qr_code = qr.make_image(fill_color="black", back_color="white")

        return self.qr_code
    
    def download_images(self, allimages = False):
        "Downloads all images in a post, puts images into downloaded_images"
        self.downloaded_images = { }

        #Get featured image
        if hasattr(self, "featured_image"):
            print("Found featured image!")
            self.downloaded_images['featured'] = Methods.download_image(self.featured_image['url'])
            
        #Download other images in article, if it's asked or if a custom_feature is set.
        if allimages or (hasattr(self, "custom_feature") and self.custom_feature):
            print("Downloading other images...")
            for index, image in enumerate(self.images):
                self.downloaded_images['img_' + str(index)] = Methods.download_image(image['url'])
                print("Image downloaded!")

        return self.downloaded_images

    def zip_images(self, zip_buffer : Methods.ZipBuilder, allimages = False):
        if not hasattr(self, "downloaded_images"):
            self.download_images()
        
        if not hasattr(self, "downloaded_images") and self.downloaded_images:
            self.download_images()
        
        zip_path = ""

        if hasattr(self, "featured_image") and self.featured_image:
            zip_path = Path(DEFAULT_IMG_SAVE_ZIP) / (str(self.id) + "_featured.jpg")
            Methods.zip_image(zip_buffer, zip_path)

        
        if not hasattr(self,"qr_code"):
            self.generate_qr_code()
        
        image_paths['qr_code'] = Path(DEFAULT_IMG_SAVE_ZIP) / (str(self.id) + "_qr_code.png")
        
        for image in self.downloaded_images:
             image_paths['img_' + str(index)] = Path(DEFAULT_IMG_SAVE_ZIP) / (str(self.id) + "_featured.jpg")
        
        

    def save_images(self, location, allimages = False):
        """Saves QR codes & featured image + all article images if allimages = True"""
        filepaths = { }

        if not hasattr(self, "downloaded_images"):
            self.download_images()

        #Saving featured image
        if hasattr(self, "featured_image"):
            filepaths['featured'] = Methods.save_image(self.downloaded_images['featured'], Path(location) / (str(self.id) + "_featured.jpg"))

        #Save QR code
        if (not hasattr(self,"qr_code")):
            self.generate_qr_code()
        filepaths['qr_code'] = Methods.save_image(self.qr_code, Path(location) / (str(self.id) + "_qr_code.png"))

        if (allimages):
            print("Saving all images!")
            for index, image in enumerate(self.images):
                print("Saving image.")
                saveloc = Path(location) / (str(self.id) + "_img_" + str(index) + ".png")
                filepaths['img_' + str(index)] = Methods.save_image(self.downloaded_images['img_' + str(index)], saveloc)

        self.image_paths = filepaths
        return self.image_paths

    def get_CSV_helper(self, image_paths, index = 0):
        """The shared functionality between the two CSV functions is here"""
        CSV = {
                "Title_" + chr(index + 65) : self.title,
                "Body_" + chr(index + 65) : self.body,
                "@QR_" + chr(index + 65) : image_paths['qr_code'],
                "Author_" + chr(index + 65) : self.author
                }
            
        if hasattr(self, "custom_feature") and self.custom_feature:
            CSV["@image_" + chr(index + 65)] = image_paths["img_" + str(self.custom_feature)]
        else:
            CSV["@image_" + chr(index + 65)] = image_paths["featured"]
        
        return CSV

    def get_CSV_entry_zip(self, index = 0):
        """Returns one CSV entry containing headline, article body, and local filepaths to the QR code & featured image. Gets images/QR codes into buffers"""
        
        
        return self.get_CSV_helper(image_paths, index)

    def get_CSV_entry(self, index = 0):
        """Returns one CSV entry containing headline, article body, and absolute filepaths to the QR code & featured image. Will save images/QR code"""
        if not hasattr(self, "image_paths"):
            if hasattr(self, "custom_feature"):
                self.save_images(DEFAULT_IMG_SAVE_LOC, True)
            else:
                self.save_images(DEFAULT_IMG_SAVE_LOC)

        return self.get_CSV_helper(self.image_paths, index)
            
            


class WordPressExtractor:
    def __init__(self, base_url):
        """Initialize with WordPress site URL (e.g., 'https://example.com')"""
        self.base_url = base_url.rstrip('/')
        self.api_url = urljoin(self.base_url, '/wp-json/wp/v2/')
    
    def get_posts(self, per_page=10, page=1):
        """Fetch posts from WordPress REST API"""
        url = urljoin(self.api_url, 'posts?_embed=1')
        print(url)
        params = {
            'per_page': per_page,
            'page': page,
            '_embed': True  # Include featured images and other embedded data
        }
        
        try:
            response = requests.get(url, params=params)
            response.encoding = 'utf-8'
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching posts: {e}")
            return []
    
    def extract_posts(self, posts):
        """Extract title, content, and images from posts"""
        extracted_posts = []
        
        for post in posts:
            extracted_posts.append(Post(post))
        
        return extracted_posts
    
    def get_all_posts(self, max_posts=None):
        """Fetch all posts with pagination"""
        all_posts = []
        page = 1
        per_page = 100
        
        while True:
            posts = self.get_posts(per_page=per_page, page=page)
            if not posts:
                break
            
            all_posts.extend(posts)
            
            if max_posts and len(all_posts) >= max_posts:
                all_posts = all_posts[:max_posts]
                break
            
            if len(posts) < per_page:  # Last page
                break
            
            page += 1
        
        return all_posts
    
    def generate_qr_code(self, filename=None):
        """Generate QR code for the main WordPress site"""
        if filename is None:
            # Create filename from site URL
            
            parsed_url = urlparse(self.base_url)
            site_name = parsed_url.netloc.replace('.', '_')
            filename = f"{site_name}_qr_code.png"
        
        return self.generate_qr_code(self.base_url, filename)




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
    
    def _ensure_open(self):
        """Ensure the zip file is still open for writing."""
        if self.closed:
            raise ValueError("ZipBuilder is already closed. Cannot add more content.")
    
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
        self._ensure_open()
        
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
        self._ensure_open()
        
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
        self._ensure_open()
        
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
        self._ensure_open()
        
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
        self._ensure_open()
        
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


# Example usage and demonstration
if __name__ == "__main__":
    # Create some sample images
    red_img = Image.new('RGB', (100, 100), 'red')
    blue_img = Image.new('RGB', (150, 150), 'blue')
    green_img = Image.new('RGB', (200, 200), 'green')
    
    # Example 1: Method chaining
    builder = ZipBuilder()
    zip_bytes = (builder
                .add_image(red_img, 'photos/', 'sunset.jpg', 'JPEG')
                .add_image(blue_img, 'thumbnails/')  # Auto-generated filename
                .add_text('This is a sample zip file!', 'readme.txt')
                .add_csv([['Name', 'Age'], ['Alice', 25], ['Bob', 30]], 'data.csv', 'reports/')
                .getvalue())
    
    print(f"Created zip with {len(zip_bytes)} bytes")
    
    # Example 2: Step by step
    builder2 = ZipBuilder()
    builder2.add_image(green_img, 'assets/images/', 'logo.png')
    builder2.add_text('Config settings here', 'config.txt', 'settings/')
    
    print(f"Files in zip: {builder2.list_contents()}")
    print(f"Zip info: {builder2.get_info()}")
    
    # Save to file
    builder2.save_to_file('example_output.zip')
    
    # Example 3: Context manager (automatic cleanup)
    with ZipBuilder() as zip_ctx:
        zip_ctx.add_image(red_img, 'photos/', 'red.png')
        zip_ctx.add_image(blue_img, 'photos/', 'blue.png')
        zip_ctx.add_text('Generated automatically', 'auto.txt')
        
        context_zip = zip_ctx.getvalue()
    
    print(f"Context manager zip: {len(context_zip)} bytes")
    
    # Example 4: Adding different types of content
    mixed_builder = ZipBuilder()
    mixed_builder.add_image(red_img, 'images/')
    mixed_builder.add_bytes(b'Raw binary data', 'data.bin', 'binary/')
    
    # You can check contents before finalizing
    print(f"Mixed zip contains: {mixed_builder.list_contents()}")
    
    final_mixed = mixed_builder.getvalue()
    print(f"Final mixed zip: {len(final_mixed)} bytes")

# Usage example
if __name__ == "__main__":
    # Replace with your WordPress site URL
    wp_site = "https://thefrontpagefrcc.com"
    
    extractor = WordPressExtractor(wp_site)
    
    ## Generate QR code for the main site
    #print("Generating QR code for the main site...")
    #site_qr = extractor.generate_site_qr_code()
    
    # Get first 5 posts
    raw_posts = extractor.get_posts(per_page=5)
    
    if raw_posts:
        # Extract data
        posts = extractor.extract_posts(raw_posts)
        
        for post in posts:
            print(post.get_CSV_entry())
        
    else:
        print("No posts found or API not accessible")
