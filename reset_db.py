from app import app, db

with app.app_context():
    # This will drop all existing tables and create new ones
    db.drop_all()
    db.create_all()
    print("Database has been reset successfully!") 