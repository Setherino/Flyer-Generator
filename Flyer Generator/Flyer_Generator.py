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

DEFAULT_IMG_SAVE_LOC = "images/"
DEFAULT_CSV_SAVE_LOC = "CSV_FILES/"
### Adobe docs specify that DataMerge should work with paths relative to the CSV, but it does not, so leave this field empty.
DEFAULT_IMG_SAVE_ZIP = "" 
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
            self.downloaded_images[self.featured_key()] = Methods.download_image(self.featured_image['url'])
            
        #Download other images in article, if it's asked or if a custom_feature is set.
        if allimages or (hasattr(self, "custom_feature") and self.custom_feature):
            print("Downloading other images...")
            for index, image in enumerate(self.images):
                self.downloaded_images[self.img_key(index)] = Methods.download_image(image['url'])
                print("Image downloaded!")

        return self.downloaded_images

    def featured_key(self):
        """Returns standard key for featured image"""
        return 'featured'

    def img_key(self, index):
        """Returns standard key for article images"""
        return 'img_' + str(index)

    def qr_key(self):
        """Returns standard key for qr code"""
        return 'qr_code'


    def get_featured_filename(self):
        """Returns standard filename for featured image"""
        return str(self.id) + "_featured.png"

    def get_img_filename(self, index):
        """Returns standard filename for article images"""
        return str(self.id) + "_img_" + str(index) + ".png"

    def get_qr_filename(self):
        """Returns standard filename for qr code"""
        return str(self.id) + "_qr_code.png"

    def zip_images(self, zip_buffer : Methods.ZipBuilder, allimages = False):
        """Add all post images into a Zip file, generate/downloads images where necessary"""
        if not hasattr(self, "downloaded_images"):
            self.download_images()

        zip_paths = { }

        if hasattr(self, "featured_image") and self.featured_image:
            zip_buffer.add_image(self.downloaded_images[self.featured_key()], DEFAULT_IMG_SAVE_ZIP, self.get_featured_filename())
            zip_paths[self.featured_key()] = DEFAULT_IMG_SAVE_ZIP + self.get_featured_filename()
        
        if not hasattr(self,"qr_code"):
            self.generate_qr_code()
        
        zip_buffer.add_image(self.qr_code, DEFAULT_IMG_SAVE_ZIP, self.get_qr_filename())
        zip_paths[self.qr_key()] = DEFAULT_IMG_SAVE_ZIP + self.get_qr_filename()

        article_images = {k: v for k, v in self.downloaded_images.items() if k != self.featured_key()}
        if hasattr(self, 'custom_feature') and self.custom_feature:
            for index, image in enumerate(article_images):
                zip_buffer.add_image(self.downloaded_images[self.img_key(index)], DEFAULT_IMG_SAVE_ZIP, self.get_img_filename(index))
                zip_paths[self.img_key(index)] = DEFAULT_IMG_SAVE_ZIP + self.get_img_filename(index)
        
        self.image_paths = zip_paths
        return zip_buffer

    def get_CSV_helper(self, image_paths, index = 0):
        """Returns one CSV entry containing headline, article body, and absolute filepaths to the QR code & featured image. Will save images/QR code"""
        CSV = {
                "Title_" + chr(index + 65) : self.title,
                "Body_" + chr(index + 65) : self.body,
                "@QR_" + chr(index + 65) : image_paths[self.qr_key()],
                "Author_" + chr(index + 65) : self.author
                }
            
        if hasattr(self, "custom_feature") and self.custom_feature:
            CSV["@image_" + chr(index + 65)] = image_paths[self.img_key(self.custom_feature)]
        else:
            CSV["@image_" + chr(index + 65)] = image_paths[self.featured_key()]
        
        return CSV

    def get_CSV_entry_zip(self, index = 0):
        """Returns one CSV entry containing post info."""
        
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

        for i, post in enumerate(posts):
            
            pass

    def extract_posts(self, posts):
        """Extract title, content, and images from posts"""
        extracted_posts = []
        
        for post in posts:
            extracted_posts.append(Post(post))

        self.posts = extracted_posts
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
