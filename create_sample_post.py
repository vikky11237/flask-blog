from app import app, db, Post, User
from datetime import datetime

sample_post = {
    'title': 'Welcome to Our New Blog',
    'content': '''
    Welcome to our new blog! This is our first post to demonstrate the functionality of our blogging platform.

    Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.

    Key Features of Our Blog:
    • Clean and responsive design
    • Comment system for engaging discussions
    • Admin-only posting capabilities
    • User authentication

    Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

    Stay tuned for more updates!
    '''
}

def create_sample_post():
    with app.app_context():
        # Get the admin user (assuming username is 'admin')
        admin = User.query.filter_by(username='admin').first()
        
        if not admin:
            print("Error: Admin user not found! Please create an admin user first.")
            return
        
        # Create the post
        post = Post(
            title=sample_post['title'],
            content=sample_post['content'],
            user_id=admin.id,
            created_at=datetime.utcnow()
        )
        
        db.session.add(post)
        db.session.commit()
        print(f"Sample post '{post.title}' created successfully!")

if __name__ == "__main__":
    create_sample_post() 