from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from PIL import Image
import os
from flask_mail import Mail, Message
import secrets
from config import RESEND_API_KEY, DEFAULT_SENDER_EMAIL
import resend
import io
import time

# Create Flask app
app = Flask(__name__)

# Basic configuration
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

# Configure Resend
resend.api_key = RESEND_API_KEY

# Initialize extensions
db = SQLAlchemy(app)
mail = Mail(app)

# Add these configurations after app initialization
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Add these configurations after the existing UPLOAD_FOLDER config
MAX_IMAGE_SIZE = (800, 800)  # Maximum width and height
THUMBNAIL_SIZE = (300, 300)  # Size for thumbnails in the post list

def send_email(to_email, subject, content):
    try:
        params = {
            "from": DEFAULT_SENDER_EMAIL,
            "to": to_email,
            "subject": subject,
            "html": content
        }
        
        response = resend.Emails.send(params)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def resize_image(image_file):
    # Open the image using Pillow
    img = Image.open(image_file)
    
    # Convert image to RGB if it's not
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Calculate new dimensions while maintaining aspect ratio
    width_ratio = MAX_IMAGE_SIZE[0] / img.width
    height_ratio = MAX_IMAGE_SIZE[1] / img.height
    ratio = min(width_ratio, height_ratio)
    
    if ratio < 1:  # Only resize if image is larger than maximum size
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    
    # Save the resized image to a bytes buffer
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=85, optimize=True)
    buffer.seek(0)
    
    return buffer

def create_thumbnail(image_file):
    img = Image.open(image_file)
    
    # Convert image to RGB if it's not
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Calculate dimensions for center crop
    width, height = img.size
    target_ratio = THUMBNAIL_SIZE[0] / THUMBNAIL_SIZE[1]  # width / height
    current_ratio = width / height
    
    if current_ratio > target_ratio:
        # Image is wider than needed
        new_width = int(height * target_ratio)
        left = (width - new_width) // 2
        img = img.crop((left, 0, left + new_width, height))
    else:
        # Image is taller than needed
        new_height = int(width / target_ratio)
        top = (height - new_height) // 2
        img = img.crop((0, top, width, top + new_height))
    
    # Resize to final thumbnail size
    img = img.resize(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
    
    # Enhance the thumbnail slightly
    from PIL import ImageEnhance
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.2)  # Slight sharpening
    
    # Save thumbnail to a bytes buffer with higher quality
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=90, optimize=True)
    buffer.seek(0)
    
    return buffer

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100))
    bio = db.Column(db.Text)
    profile_pic = db.Column(db.String(100), default='default_profile.png')
    is_admin = db.Column(db.Boolean, default=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    posts = db.relationship('Post', backref='user', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class PasswordResetRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')
    admin_notes = db.Column(db.Text)
    user = db.relationship('User', backref='reset_requests')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            session['name'] = user.name
            session['profile_pic'] = user.profile_pic
            
            # Check if there's a next URL stored in session
            next_url = session.pop('next_url', None)
            if next_url:
                return redirect(next_url)
                
            return redirect(url_for('index'))
            
        flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        email = request.form.get('email')
        name = request.form.get('name')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')
            
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return render_template('register.html')
            
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return render_template('register.html')
            
        user = User(
            username=username,
            password=generate_password_hash(password),
            email=email,
            name=name,
            is_admin=False
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/')
def index():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('index.html', posts=posts)

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post_detail.html', post=post)

@app.route('/create_post', methods=['GET', 'POST'])
def create_post():
    if not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        image = request.files.get('image')
        
        if title and content:
            post = Post(
                title=title,
                content=content,
                user_id=session.get('user_id')
            )
            
            if image and image.filename:
                filename = secure_filename(image.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(image_path)
                post.image = filename
                
            db.session.add(post)
            db.session.commit()
            
            flash('Post created successfully!', 'success')
            return redirect(url_for('index'))
            
        flash('Title and content are required!', 'danger')
        
    return render_template('create_post.html')

@app.route('/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    if not session.get('user_id'):
        flash('Please login to comment', 'danger')
        return redirect(url_for('login'))
        
    content = request.form.get('content')
    comment = Comment(
        content=content,
        user_id=session['user_id'],
        post_id=post_id
    )
    db.session.add(comment)
    db.session.commit()
    
    flash('Comment added successfully!', 'success')
    return redirect(url_for('post_detail', post_id=post_id))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if not session.get('user_id'):
        flash('Please login first', 'danger')
        return redirect(url_for('login'))
        
    user = User.query.get_or_404(session['user_id'])
    
    if request.method == 'POST':
        update_type = request.form.get('update_type')
        
        if update_type == 'profile_pic' and 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                profile_pic = f"profile_{user.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], profile_pic)
                file.save(file_path)
                
                # Resize image
                with Image.open(file_path) as img:
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    width, height = img.size
                    size = min(width, height)
                    left = (width - size) // 2
                    top = (height - size) // 2
                    right = left + size
                    bottom = top + size
                    
                    img = img.crop((left, top, right, bottom))
                    img = img.resize((200, 200), Image.Resampling.LANCZOS)
                    img.save(file_path, quality=95)
                
                user.profile_pic = profile_pic
                session['profile_pic'] = profile_pic
                db.session.commit()
                flash('Profile picture updated successfully!', 'success')
                
        elif update_type == 'profile_info':
            user.name = request.form.get('name', user.name)
            user.email = request.form.get('email', user.email)
            user.bio = request.form.get('bio', user.bio)
            session['name'] = user.name
            
            db.session.commit()
            flash('Profile information updated successfully!', 'success')
            
        return redirect(url_for('profile'))
        
    return render_template('profile.html', user=user)

@app.route('/admin/users')
def admin_users():
    if not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/toggle_admin/<int:user_id>', methods=['POST'])
def toggle_admin(user_id):
    if not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    
    # Prevent self-demotion
    if user.id == session.get('user_id'):
        flash('You cannot modify your own admin status.', 'danger')
        return redirect(url_for('admin_users'))
    
    user.is_admin = not user.is_admin
    db.session.commit()
    
    action = "promoted to" if user.is_admin else "demoted from"
    flash(f'User {user.username} has been {action} admin.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/reset_password/<int:user_id>', methods=['POST'])
def admin_reset_password(user_id):
    if not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    
    # Prevent self-password reset through this route
    if user.id == session.get('user_id'):
        flash('You cannot reset your own password through this route.', 'danger')
        return redirect(url_for('admin_users'))
    
    # Reset password to default: 123123
    default_password = "123123"
    user.password = generate_password_hash(default_password)
    db.session.commit()
    
    flash(f'Password for user {user.username} has been reset to: {default_password}', 'success')
    return redirect(url_for('admin_users'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            token = secrets.token_urlsafe(32)
            reset_request = PasswordResetRequest(
                user_id=user.id,
                token=token
            )
            db.session.add(reset_request)
            db.session.commit()
            
            admin_users = User.query.filter_by(is_admin=True).all()
            
            # Send to each admin
            for admin in admin_users:
                reset_link = url_for('admin_handle_reset', token=token, _external=True)
                email_content = f"""
                <h2>Password Reset Request</h2>
                <p>A password reset has been requested for user: <strong>{user.username}</strong></p>
                <p>Email: {user.email}<br>
                Requested at: {reset_request.created_at}</p>
                <p>To handle this request, please click the following link:</p>
                <p><a href="{reset_link}">{reset_link}</a></p>
                <p>This request will expire in 24 hours.</p>
                """
                
                send_email(
                    admin.email,
                    'Password Reset Request',
                    email_content
                )
            
            flash('Your password reset request has been sent to the administrators.', 'info')
            return redirect(url_for('login'))
            
        flash('If an account exists with that email, a password reset request has been sent.', 'info')
        return redirect(url_for('forgot_password'))
        
    return render_template('forgot_password.html')

@app.route('/admin/reset-requests')
def admin_reset_requests():
    if not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
        
    requests = PasswordResetRequest.query.order_by(PasswordResetRequest.created_at.desc()).all()
    return render_template('admin_reset_requests.html', requests=requests)

@app.route('/admin/handle-reset/<token>', methods=['GET', 'POST'])
def admin_handle_reset(token):
    if not session.get('user_id'):
        session['next_url'] = url_for('admin_handle_reset', token=token)
        flash('Please login to handle the password reset request.', 'info')
        return redirect(url_for('login'))
        
    if not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
        
    reset_request = PasswordResetRequest.query.filter_by(token=token).first_or_404()
    
    if request.method == 'POST':
        action = request.form.get('action')
        notes = request.form.get('admin_notes')
        
        try:
            if action == 'approve':
                # Import secrets if not already imported
                import secrets
                
                # Generate new password
                new_password = secrets.token_urlsafe(8)
                print(f"Debug - Generated password: {new_password}")  # Debug log
                
                # Update user password
                reset_request.user.password = generate_password_hash(new_password)
                reset_request.status = 'approved'
                reset_request.admin_notes = notes
                
                print(f"Debug - Sending email to: {reset_request.user.email}")  # Debug log
                
                # Send approval email with new password
                params = {
                    "from": DEFAULT_SENDER_EMAIL,
                    "to": reset_request.user.email,
                    "subject": "Password Reset Request Approved",
                    "html": f"""
                        <h2>Password Reset Approved</h2>
                        <p>Your password reset request has been approved.</p>
                        <p>Your new temporary password is: <strong>{new_password}</strong></p>
                        <p>Please login with this password and change it immediately for security purposes.</p>
                        <p>If you did not request this password reset, please contact the administrators immediately.</p>
                    """
                }
                
                # Send email
                print("Debug - Sending email...")  # Debug log
                email_response = resend.Emails.send(params)
                print(f"Debug - Email response: {email_response}")  # Debug log
                
                # Commit changes
                db.session.commit()
                print("Debug - Database committed")  # Debug log
                
                flash('Password reset approved and email sent to user.', 'success')
                
            elif action == 'reject':
                reset_request.status = 'rejected'
                reset_request.admin_notes = notes
                
                # Send rejection email
                params = {
                    "from": DEFAULT_SENDER_EMAIL,
                    "to": reset_request.user.email,
                    "subject": "Password Reset Request Rejected",
                    "html": f"""
                        <h2>Password Reset Request Rejected</h2>
                        <p>Your password reset request has been rejected by an administrator.</p>
                        <p><strong>Admin Notes:</strong> {notes if notes else 'No notes provided.'}</p>
                        <p>If you still need to reset your password, please submit a new request or contact the administrators directly.</p>
                    """
                }
                
                resend.Emails.send(params)
                db.session.commit()
                flash('Password reset rejected and email sent to user.', 'success')
            
            return redirect(url_for('admin_reset_requests'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error details: {str(e)}")  # Detailed error log
            flash(f'Error processing request: {str(e)}', 'danger')  # Show actual error
            return redirect(url_for('admin_handle_reset', token=token))
        
    return render_template('admin_handle_reset.html', reset_request=reset_request)

@app.route('/test-email')
def test_email():
    try:
        params = {
            "from": DEFAULT_SENDER_EMAIL,
            "to": "vikky11237@gmail.com",  # Your email address where you want to receive the test mail
            "subject": "Test Email from Flask Blog",
            "html": """
                <h1>Test Email</h1>
                <p>This is a test email from your Flask Blog application.</p>
                <p>If you're seeing this, your email configuration is working!</p>
                <p>Time sent: {}</p>
            """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        }
        
        response = resend.Emails.send(params)
        return f'Test email sent! Check your inbox. Response: {response}'
    except Exception as e:
        return f'Error sending email: {str(e)}'

@app.route('/edit_post/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    if not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
        
    post = Post.query.get_or_404(post_id)
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        image = request.files.get('image')
        
        if title and content:
            post.title = title
            post.content = content
            
            if image and image.filename:
                filename = secure_filename(image.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(image_path)
                post.image = filename
                
            db.session.commit()
            flash('Post updated successfully!', 'success')
            return redirect(url_for('index'))
            
        flash('Title and content are required!', 'danger')
        
    return render_template('edit_post.html', post=post)

@app.route('/delete_post/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    if not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
        
    post = Post.query.get_or_404(post_id)
    
    # Delete the post image if it exists
    if post.image:
        try:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], post.image)
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception as e:
            print(f"Error deleting image: {e}")
    
    db.session.delete(post)
    db.session.commit()
    
    flash('Post deleted successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if not session.get('user_id'):
        flash('Please login to edit your profile.', 'danger')
        return redirect(url_for('login'))
        
    user = User.query.get_or_404(session['user_id'])
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        email = request.form.get('email')
        bio = request.form.get('bio')
        profile_pic = request.files.get('profile_pic')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        try:
            # Update basic info
            user.name = name
            user.email = email
            user.bio = bio
            
            # Handle profile picture upload
            if profile_pic and profile_pic.filename:
                filename = secure_filename(profile_pic.filename)
                # Add timestamp to filename to prevent caching issues
                filename = f"{int(time.time())}_{filename}"
                profile_pic.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                
                # Delete old profile picture if it exists and isn't the default
                if user.profile_pic and user.profile_pic != 'default_profile.png':
                    try:
                        old_pic_path = os.path.join(app.config['UPLOAD_FOLDER'], user.profile_pic)
                        if os.path.exists(old_pic_path):
                            os.remove(old_pic_path)
                    except Exception as e:
                        print(f"Error deleting old profile picture: {e}")
                
                user.profile_pic = filename
                session['profile_pic'] = filename  # Update session
            
            # Handle password change
            if current_password and new_password and confirm_password:
                if not check_password_hash(user.password, current_password):
                    flash('Current password is incorrect.', 'danger')
                    return redirect(url_for('edit_profile'))
                    
                if new_password != confirm_password:
                    flash('New passwords do not match.', 'danger')
                    return redirect(url_for('edit_profile'))
                    
                user.password = generate_password_hash(new_password)
            
            db.session.commit()
            
            # Update session data
            session['name'] = user.name
            
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile', username=user.username))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating profile: {e}")
            flash('Error updating profile. Please try again.', 'danger')
            
    return render_template('edit_profile.html', user=user)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)