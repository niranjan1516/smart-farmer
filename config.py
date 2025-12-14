import os

class Config:
    # 1. Secret Key: Protects the login session from hackers
    SECRET_KEY = 'mca_project_secret_key'

    # 2. Database Connection String
    # Format: postgresql://username:password@localhost/database_name
    # REPLACE 'your_password' with your actual Postgres password!
    # REPLACE 'postgres' if your username is different.
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:niranjan@localhost/smartfarmer_db'

    # 3. Performance Setting: Turn off unnecessary tracking to save memory
    SQLALCHEMY_TRACK_MODIFICATIONS = False

# Examiner Note: "I used a Config class to separate sensitive data from the main logic."