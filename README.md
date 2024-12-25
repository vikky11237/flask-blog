# Flask Blog Application

A modern blog application built with Flask, featuring user authentication, admin controls, and a clean, responsive design.

## Features

- 🔐 User Authentication
  - Login/Register system
  - Password reset functionality
  - Admin privileges

- 📝 Blog Management
  - Create, edit, and delete posts
  - Image upload support
  - Rich text content
  - Post thumbnails

- 👤 User Profiles
  - Customizable profile pictures
  - Bio and personal information
  - Profile editing

- 🎨 Modern Design
  - Responsive layout
  - Clean and intuitive interface
  - Dark theme

## Technologies Used

- Python 3.x
- Flask
- SQLAlchemy
- Pillow (PIL)
- HTML/CSS
- Bootstrap 5
- SQLite

## Installation

1. Clone the repository

bash
git clone https://github.com/YOUR_USERNAME/flask-blog.git
cd flask-blog


2. Create a virtual environment
   bash
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate


3. Install dependencies

pip install -r requirements.txt


4. Set up the database
   bash
python
>>> from app import app, db
>>> with app.app_context():
... db.create_all()
>>>

5. Create an admin user
   bash
python create_admin.py

6. Run the application
bash
python app.py
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key
RESEND_API_KEY=your-resend-api-key


## Project Structure

flask-blog/
├── static/
│ └── uploads/ # User uploaded files
├── templates/ # HTML templates
├── app.py # Main application file
├── config.py # Configuration settings
├── create_admin.py # Admin user creation script
└── requirements.txt # Project dependencies

## Contributing

1. Fork the repository
2. Create a new branch (`git checkout -b feature/improvement`)
3. Make your changes
4. Commit your changes (`git commit -am 'Add new feature'`)
5. Push to the branch (`git push origin feature/improvement`)
6. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

Your Name - [vikky11237@gmail.com](mailto:vikky11237@gmail.com)

Project Link: [https://github.com/YOUR_USERNAME/flask-blog](https://github.com/YOUR_USERNAME/flask-blog)

Remember to:
Replace YOUR_USERNAME with your actual GitHub username
Update the email if you want to use a different one
Add any additional features or technologies you've implemented
Update the installation steps if you have any specific requirements
