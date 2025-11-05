import os
from dotenv import load_dotenv

load_dotenv()

API_DIR = os.path.dirname(os.path.abspath(__file__)) 

ROOT_DIR = os.path.dirname(API_DIR) 

class Config:
    DEBUG = True
    SECRET_KEY = os.getenv("SECRET_KEY", "fiap-secret")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret")
    
    DATA_PATH = os.path.join(ROOT_DIR, "data", "books.csv")