import streamlit as st
import pandas as pd
from PIL import Image
import io
import base64
from Flyer_Generator import WordPressExtractor, Post
import tempfile
import os
import re

#global variables
editor = "John Doe"
copy_editor = "Jane Doe"
advisor = "Joe Doe"
date_printed = "01/01/1980"

# Set page config
st.set_page_config(
    page_title="Student Newspaper Flyer Generator",
    page_icon=":newspaper:",
    layout="wide"
)

def image_to_base64(image):
    """Convert PIL Image to base64 string for display"""
    if image is None:
        return None
    
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode()

def display_image_selector(post, post_index):
    """Display image selector for a post"""
    available_images = {}
    
    # Add featured image if available
    if hasattr(post, 'featured_image') and post.featured_image:
        available_images['Featured Image'] = post.featured_image
    
    # Add other images from the post
    for i, img in enumerate(post.images):
        available_images[f'Article Image {i+1}'] = img
    
    if not available_images:
        st.write("No images available for this post")
        return None, None
    
    # Image selection dropdown
    selected_image_key = st.selectbox(
        "Select Image:",
        list(available_images.keys()),
        key=f"img_select_{post_index}"
    )
    
     #Update the post with the new image
    img_index = re.search(r'\d+$', selected_image_key)
    if img_index:
        post.custom_feature = int(img_index.group()) - 1
        print("Set custom image: " + str(post.custom_feature))
    
    
    selected_image = available_images[selected_image_key]
    
    # Display selected image if it exists in downloaded images
    if hasattr(post, 'downloaded_images'):
        if selected_image_key == 'Featured Image' and 'featured' in post.downloaded_images:
            display_img = post.downloaded_images['featured']
        else:
            # Find corresponding downloaded image
            for i, img in enumerate(post.images):
                if img == selected_image and f'img_{i}' in post.downloaded_images:
                    display_img = post.downloaded_images[f'img_{i}']
                    break
            else:
                display_img = None
        
        if display_img:
            st.image(display_img, width=300, caption=selected_image.get('alt', 'Post Image'))
        else:
            st.write(f"Image not downloaded yet: {selected_image.get('url', 'No URL')}")
    else:
        st.write(f"Images not downloaded yet. URL: {selected_image.get('url', 'No URL')}")
    
    return selected_image_key, selected_image

def display_post_card(post, index, total_posts, is_expanded=False):
    """Display a single post card with all required information"""
    
    # Create main layout with buttons on the side
    col_buttons, col_content = st.columns([1, 12])
    
    with col_buttons:
        st.write("")  # Add some spacing
        if index > 0:  # Not the first post
            if st.button("↑", key=f"move_up_{index}", help="Move up"):
                move_post_up(index)
        
        if index < total_posts - 1:  # Not the last post
            if st.button("↓", key=f"move_down_{index}", help="Move down"):
                move_post_down(index)
    
    with col_content:
        # Create expandable container for each post
        with st.expander(f"{index + 1}. {post.title[:50]}{'...' if len(post.title) > 50 else ''}", expanded=is_expanded):
            # Create columns for layout
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader("Images")
                # Image selector and display
                selected_img_key, selected_img = display_image_selector(post, index)
                
                # QR Code section
                st.subheader("QR Code")
                if hasattr(post, 'qr_code') and post.qr_code:
                    # Convert PIL Image to bytes for Streamlit
                    img_buffer = io.BytesIO()
                    post.qr_code.save(img_buffer, format='PNG')
                    img_buffer.seek(0)
                    st.image(img_buffer, width=150, caption="Link to article")
                else:
                    if st.button(f"Generate QR Code", key=f"qr_{index}"):
                        with st.spinner("Generating QR code..."):
                            post.generate_qr_code()
                            st.rerun()
            
            with col2:
                st.subheader("Article Details")
                
                # Title (editable)
                title = st.text_input(
                    "Title:",
                    value=post.title,
                    key=f"title_{index}"
                )
                
                # Article body (editable)
                body = st.text_area(
                    "Body:",
                    value=post.body,
                    height=200,
                    key=f"body_{index}"
                )
                
                # Post metadata
                st.write(f"**Post ID:** {post.id}")
                st.write(f"**Date:** {post.date}")
                st.write(f"**Link:** [View Article]({post.link})")
            
            # Action buttons
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            
            with col_btn1:
                if st.button(f"Download Images", key=f"download_{index}"):
                    with st.spinner("Downloading images..."):
                        post.download_images(True)
                        st.success("Images downloaded!")
                        st.rerun()
            
            with col_btn2:
                if st.button(f"Save Images", key=f"save_{index}"):
                    with st.spinner("Saving images..."):
                        post.save_images("Images/", allimages=True)
                        st.success("Images saved!")
                        st.rerun()
            
            with col_btn3:
                if st.button(f"Generate CSV Entry", key=f"csv_{index}"):
                    csv_entry = post.get_CSV_entry(index)
                    st.json(csv_entry)


def handle_text_change():
    pass

def main():
    st.title("Student Newspaper Flyer Generator")
    st.markdown("---")
    
    editor = st.text_input(
    "Editor-in-Chief:",
    value="John Doe",
    on_change=handle_text_change,
    key="editor_textbox"
    )
    copy_editor = st.text_input(
    "Copy Editor:",
    value="Jane Doe",
    on_change=handle_text_change,
    key="copy_editor_textbox"
    )
    advisor = st.text_input(
    "Advisor:",
    value="Joe Doe",
    on_change=handle_text_change,
    key="advisor_textbox"
    )
    date_printed = st.text_input(
    "Date Printed:",
    value="01/01/1980",
    on_change=handle_text_change,
    key="date_printed_textbox"
    )
    

    # Sidebar for WordPress site configuration
    with st.sidebar:
        st.header("Configuration")
        
        # WordPress site URL
        wp_url = st.text_input(
            "WordPress Site URL:",
            value="https://thefrontpagefrcc.com",
            help="Enter your WordPress site URL"
        )
        
        # Number of posts to fetch
        num_posts = st.number_input(
            "Number of Posts to Fetch:",
            min_value=1,
            max_value=50,
            value=5,
            help="How many recent posts to fetch from WordPress"
        )
        
        # Fetch posts button
        if st.button("Fetch Posts", type="primary"):
            fetch_posts(wp_url, num_posts)
    
    # Main content area
    if 'posts' not in st.session_state:
        st.info("Please fetch posts from your WordPress site using the sidebar.")
        return
    
    if not st.session_state.posts:
        st.warning("No posts found. Please check your WordPress site URL and try again.")
        return
    
    # Post management section
    st.header(f"Manage Posts ({len(st.session_state.posts)} posts loaded)")
    
    # Bulk actions
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Download All Images"):
            download_all_images()
    
    with col2:
        if st.button("Save All Images"):
            save_all_images()
    
    with col3:
        if st.button("Generate All CSV Entries"):
            generate_all_csv()
    
    st.markdown("---")
    
    st.markdown("---")
    
    # Display each post
    for i, post in enumerate(st.session_state.posts):
        display_post_card(post, i, len(st.session_state.posts), is_expanded=(i == 0))  # First post expanded by default
        st.markdown("---")

def fetch_posts(wp_url, num_posts):
    """Fetch posts from WordPress site"""
    try:
        with st.spinner(f"Fetching {num_posts} posts from {wp_url}..."):
            extractor = WordPressExtractor(wp_url)
            raw_posts = extractor.get_posts(per_page=num_posts)
            
            if raw_posts:
                posts = extractor.extract_posts(raw_posts)
                st.session_state.posts = posts
                st.success(f"Successfully fetched {len(posts)} posts!")
                st.rerun()
            else:
                st.error("No posts found or API not accessible")
    
    except Exception as e:
        st.error(f"Error fetching posts: {str(e)}")

def download_all_images():
    """Download images for all posts"""
    if 'posts' not in st.session_state:
        return
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, post in enumerate(st.session_state.posts):
        status_text.text(f"Downloading images for post {i+1}/{len(st.session_state.posts)}: {post.title[:30]}...")
        post.download_images(True)
        progress_bar.progress((i + 1) / len(st.session_state.posts))
    
    status_text.text("All images downloaded!")
    st.success("All images have been downloaded!")

def save_all_images():
    """Save images for all posts"""
    if 'posts' not in st.session_state:
        return
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, post in enumerate(st.session_state.posts):
        status_text.text(f"Saving images for post {i+1}/{len(st.session_state.posts)}: {post.title[:30]}...")
        if not hasattr(post, 'downloaded_images'):
            post.download_images(True)
        post.save_images("Images/", allimages=True)
        progress_bar.progress((i + 1) / len(st.session_state.posts))
    
    status_text.text("All images saved!")
    st.success("All images have been saved!")

def generate_all_csv():
    """Generate CSV entries for all posts"""
    if 'posts' not in st.session_state:
        return
    
    
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    header = [ ]
    row = [ ]

    for i, post in enumerate(st.session_state.posts):
        status_text.text(f"Generating CSV entry for post {i+1}/{len(st.session_state.posts)}: {post.title[:30]}...")
        csv_entry = post.get_CSV_entry(i)
        # Would make more sense for each post to be its own row with the same header, but inDesign Data Merge is kind of annoying.
        # It basically only ever wants to merge one row of a CSV, there are ways around this in ID but it's inflexible, so we just put everything in one row
        if csv_entry:
            for k,j in csv_entry.items():
                header.append(k)
                row.append(j)
        else:
            print("Error: No Posts!")
            return
        progress_bar.progress((i + 1) / len(st.session_state.posts))
    
    header.append('editor')
    row.append(editor)
    header.append('copy_editor')
    row.append(copy_editor)
    header.append('advisor')
    row.append(advisor)
    header.append('date_printed')
    row.append(date_printed)

    # Create DataFrame and display
    df = pd.DataFrame([row],columns=header)
    
    status_text.text("All CSV entries generated!")
    st.success("All CSV entries have been generated!")
    
    # Display the data
    st.subheader("Generated CSV Data")
    st.dataframe(df, use_container_width=True)
    
    # Download button for CSV
    csv_string = df.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv_string,
        file_name="flyer_posts.csv",
        mime="text/csv"
    )

def move_post_up(index):
    """Move a post up in the list"""
    if index > 0 and 'posts' in st.session_state:
        posts = st.session_state.posts
        posts[index], posts[index - 1] = posts[index - 1], posts[index]
        st.session_state.posts = posts
        st.rerun()

def move_post_down(index):
    """Move a post down in the list"""
    if 'posts' in st.session_state and index < len(st.session_state.posts) - 1:
        posts = st.session_state.posts
        posts[index], posts[index + 1] = posts[index + 1], posts[index]
        st.session_state.posts = posts
        st.rerun()

def apply_reordering():
    """Apply the new ordering based on user input"""
    if 'posts' not in st.session_state:
        return
    
    # Get all the position values
    positions = []
    for i in range(len(st.session_state.posts)):
        pos = st.session_state.get(f"pos_{i}", i + 1)
        positions.append((pos - 1, i))  # Convert to 0-based indexing
    
    # Sort by desired position
    positions.sort(key=lambda x: x[0])
    
    # Reorder posts
    new_order = []
    for pos, original_index in positions:
        new_order.append(st.session_state.posts[original_index])
    
    st.session_state.posts = new_order
    st.success("Posts have been reordered!")
    st.rerun()

if __name__ == "__main__":
    main()