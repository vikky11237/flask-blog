from PIL import Image, ImageDraw, ImageFont
import os

def create_default_profile():
    # Create a 200x200 image with a dark background
    img = Image.new('RGB', (200, 200), '#375a7f')
    draw = ImageDraw.Draw(img)
    
    # Draw a circle for the avatar background
    draw.ellipse([10, 10, 190, 190], fill='#2b4764')
    
    # Add a simple user icon or initials
    draw.ellipse([80, 60, 120, 100], fill='#ffffff')  # Head
    draw.rectangle([70, 110, 130, 150], fill='#ffffff')  # Body
    
    # Save the image
    upload_folder = os.path.join('static', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    img.save(os.path.join(upload_folder, 'default_profile.png'))
    print("Default profile picture created successfully!")

if __name__ == "__main__":
    create_default_profile() 