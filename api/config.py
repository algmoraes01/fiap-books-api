import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv()

class Config:
    DEBUG = True
    SECRET_KEY = os.getenv("SECRET_KEY", "fiap-secret")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret")
    
    DATA_PATH = os.path.join(BASE_DIR, "..", "data", "books.csv")