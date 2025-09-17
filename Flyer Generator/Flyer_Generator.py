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
from pathlib import Path

DEFAULT_IMG_SAVE_LOC = "Images/"
DEFAULT_CSV_SAVE_LOC = "CSV_FILES/"
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
        
        # Clean up the title:
        titleSoup = BeautifulSoup(self.title, features = "html.parser")
        self.title = titleSoup.get_text(separator=' ', strip=True)

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
    
    def download_images(self):
        "Downloads all images in a post, puts images into downloaded_images"
        self.downloaded_images = { }

        #Get featured image
        if hasattr(self, "featured_image"):
            print("Found featured image!")
            self.downloaded_images['featured'] = Methods.download_image(self.featured_image['url'])
            
        #Download other images in article.
        print("Downloading other images...")
        for index, image in enumerate(self.images):
            self.downloaded_images['img_' + str(index)] = Methods.download_image(image['url'])
            print("Image downloaded!")

        return self.downloaded_images

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

    def get_CSV_entry(self, index = 0):
        """Returns one CSV entry containing headline, article body, and filepaths to the QR code & featured image"""
        if not hasattr(self, "image_paths"):
            if hasattr(self, "custom_feature"):
                self.save_images(DEFAULT_IMG_SAVE_LOC, True)
            else:
                self.save_images(DEFAULT_IMG_SAVE_LOC, True)
            
            CSV = {
                "Title_" + chr(index + 65) : self.title,
                "Body_" + chr(index + 65) : self.body,
                "@QR_" + chr(index + 65) : self.image_paths['qr_code'],
                "Author_" + chr(index + 65) : self.author
                }
            
            if (hasattr(self, "custom_feature")):
                CSV["@image_" + chr(index + 65)] = self.image_paths["img_" + tostring(self.custom_feature)]
            else:
                CSV["@image_" + chr(index + 65)] = self.image_paths["featured"]
            
            return CSV


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
