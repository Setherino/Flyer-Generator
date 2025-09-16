import requests
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import qrcode
from PIL import Image
import io

class Post:
    def __init__(self, post):
        """Initialize Post and fill variables from JSON"""
        self.featured = False
        self.recent = False
        self.id = post.get('id')
        self.title = post.get('title', {}).get('rendered', '')
        self.exerpt = post.get('excerpt', {}).get('rendered', '')
        self.date = post.get('date')
        self.link = post.get('guid', {}).get('rendered', post.get('link', ''))

        # Extract featured image from post
        if '_embedded' in post and 'wp:featuredmedia' in post['_embedded']:
            featured_media = post['_embedded']['wp:featuredmedia'][0]
            self.featured_image = {
                'url': featured_media.get('source_url'),
                'alt': featured_media.get('alt_text', ''),
                'caption': featured_media.get('caption', {}).get('rendered', '')
            }

        # Extract images from content using BeautifulSoup
        soup = BeautifulSoup(postdata['content'], 'html.parser')
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

    def generate_qr_code(self, filename, size=10, border=4):
        """Generate QR code for a given URL"""
        qr = qrcode.QRCode(
            version=1,  # Controls size (1 is smallest)
            error_correction=qrcode.constants.ERROR_CORRECT_L,  # Low error correction
            box_size=size,  # Size of each box in pixels
            border=border,  # Border size in boxes
        )
        
        qr.add_data(self.link)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        img.save(filename)

        return img

    def get_CSV_entry():


class WordPressExtractor:
    def __init__(self, base_url):
        """Initialize with WordPress site URL (e.g., 'https://example.com')"""
        self.base_url = base_url.rstrip('/')
        self.api_url = urljoin(self.base_url, '/wp-json/wp/v2/')
    
    def get_posts(self, per_page=10, page=1):
        """Fetch posts from WordPress REST API"""
        url = urljoin(self.api_url, 'posts')
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
    
    def extract_post_data(self, posts):
        """Extract title, content, and images from posts"""
        extracted_data = []
        
        for post in posts:
            extracted_data.append(Post(post))
        
        return extracted_data
    
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
            from urllib.parse import urlparse
            parsed_url = urlparse(self.base_url)
            site_name = parsed_url.netloc.replace('.', '_')
            filename = f"{site_name}_qr_code.png"
        
        return self.generate_qr_code(self.base_url, filename)

def createCSV():


# Usage example
if __name__ == "__main__":
    # Replace with your WordPress site URL
    wp_site = "https://thefrontpagefrcc.com"
    
    extractor = WordPressExtractor(wp_site)
    
    # Generate QR code for the main site
    print("Generating QR code for the main site...")
    site_qr = extractor.generate_site_qr_code()
    
    # Get first 5 posts
    posts = extractor.get_posts(per_page=5)
    
    if posts:
        # Extract data
        extracted_data = extractor.extract_post_data(posts)
        
        # Generate QR codes for individual posts
        print("Generating QR codes for individual posts...")
        post_qr_codes = extractor.generate_post_qr_codes(extracted_data)
        
        # Display results
        for i, post in enumerate(extracted_data):
            print(f"\n--- Post {i+1} ---")
            print(f"Title: {post['title']}")
            print(f"Date: {post['date']}")
            print(f"Link: {post['link']}")
            
            if post['featured_image']:
                print(f"Featured Image: {post['featured_image']['url']}")
            
            print(f"Content Preview: {post['plain_text'][:200]}...")
            print(f"Number of images in content: {len(post['images'])}")
            
            # Show QR code info
            if i < len(post_qr_codes):
                print(f"QR Code saved: {post_qr_codes[i]['qr_file']}")
            
            print("-" * 50)
            
        print(f"\nSummary:")
        print(f"- Main site QR code: wordpress_org_news_qr_code.png")
        print(f"- Individual post QR codes: {len(post_qr_codes)} files in 'qr_codes/' folder")
        
    else:
        print("No posts found or API not accessible")
