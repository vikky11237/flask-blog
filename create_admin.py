from app import app, db, User
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_admin(username, password):
    with app.app_context():
        # Check if admin already exists
        if User.query.filter_by(username=username).first():
            print(f"User {username} already exists!")
            return
        
        admin = User(
            username=username,
            password=generate_password_hash(password),
            email='admin@example.com',
            name='Administrator',
            is_admin=True,
            joined_at=datetime.utcnow()
        )
        db.session.add(admin)
        db.session.commit()
        print(f"Admin user {username} created successfully!")

if __name__ == "__main__":
    create_admin('admin', 'admin123') 