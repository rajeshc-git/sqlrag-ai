from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import pyodbc
import bcrypt
import logging
from pydantic import BaseModel
from typing import List, Optional
import secrets
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
from fastapi import UploadFile, File
import shutil
import pandas as pd
import os
from bs4 import BeautifulSoup

app = FastAPI(title="Blueshift Signup API", version="1.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EXCEL_SAVE_DIR = "C:/Temp/campaigns"


# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SQL Server connection config
DB_CONFIG = {
    "DRIVER": "{ODBC Driver 17 for SQL Server}",
    "SERVER": "4.247.166.77",
    "DATABASE": "ABICRM",
    "UID": "rajeshc",
    "PWD": "Admin@123$"
}

# Email configuration for Gmail
EMAIL_CONFIG = {
    "SMTP_SERVER": "smtp.gmail.com",
    "SMTP_PORT": 587,
    "SENDER_EMAIL": "pupsandpets.official@gmail.com",
    "SENDER_PASSWORD": "cfyb twtg blvu ofeu"  # Gmail app password for pupsandpets.official@gmail.com
}
def get_connection():
    try:
        conn_str = ";".join([f"{k}={v}" for k, v in DB_CONFIG.items()])
        return pyodbc.connect(conn_str)
    except Exception as e:
        logger.error("Database connection failed: %s", str(e))
        raise HTTPException(status_code=500, detail="Database connection error")

# Generate secure random password
def generate_password(length=8):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(characters) for _ in range(length))
    
# Send email as a background task
async def send_email(user_email: str, fullname: str, username: str, password: str):
    start_time = time.time()
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = 'Blueshift Team <pupsandpets.official@gmail.com>'
        msg['To'] = user_email
        msg['Subject'] = 'Account Creation Successful - Blueshift'

        # Plain text version
        plain_body = f"""
Dear {fullname},

Your Blueshift account has been successfully created. Below are your login credentials:

Username: {username}
Password: {password}

Please log in at https://blueshift.abi-health.com/ and change your password for security.

If you need assistance, contact support@blueshift.com.

Best regards,
The Blueshift Team

© 2025 Blueshift. All rights reserved.
        """

        # HTML version
        html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #004aad; color: white; padding: 10px; text-align: center; border-radius: 5px; }}
                    .content {{ padding: 20px; background-color: #f9f9f9; border-radius: 5px; }}
                    .credentials {{ background-color: #e0e7ff; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                    .button {{ display: inline-block; padding: 10px 20px; background-color: #004aad; color: white; text-decoration: none; border-radius: 5px; }}
                    .footer {{ margin-top: 20px; font-size: 12px; color: #666; text-align: center; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>Welcome to Blueshift</h2>
                    </div>
                    <div class="content">
                        <p>Dear {fullname},</p>
                        <p>Your Blueshift account has been successfully created. Below are your login credentials:</p>
                        <div class="credentials">
                            <p><strong>Username:</strong> {username}</p>
                            <p><strong>Password:</strong> {password}</p>
                        </div>
                        <p>Please log in and update your password to secure your account.</p>
                        <p><a href="https://blueshift.abi-health.com/" style="color: white !important" class="button">Log In to Blueshift</a></p>
                        <p>For assistance, contact our support team at <a href="mailto:support@blueshift.abi-health.com">support@blueshift.abi-health.com</a>.</p>
                        <p>Best regards,<br>The Blueshift Team</p>
                    </div>
                    <div class="footer">
                        <p>© 2025 Blueshift. All rights reserved. | <a href="mailto:support@blueshift.abi-health.com">Contact Us</a></p>
                    </div>
                </div>
            </body>
            </html>
        """

        msg.attach(MIMEText(plain_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(EMAIL_CONFIG['SMTP_SERVER'], EMAIL_CONFIG['SMTP_PORT']) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['SENDER_EMAIL'], EMAIL_CONFIG['SENDER_PASSWORD'])
            server.send_message(msg)
        logger.info("Email sent successfully to %s in %.2f seconds", user_email, time.time() - start_time)
    except Exception as e:
        logger.error("Failed to send email to %s: %s (took %.2f seconds)", user_email, str(e), time.time() - start_time)
        # Email failure is logged but does not affect signup response

# Pydantic model for response
class User(BaseModel):
    id: int
    username: str
    fullname: str
    email: str
    mobileno: Optional[str] = None
    status: str
    modules: Optional[str] = None
    role: str

# Pydantic models for request bodies
class UserCreate(BaseModel):
    username: str
    fullname: str
    email: str
    mobileno: Optional[str] = None
    status: str
    modules: str
    role: str

class UserUpdate(BaseModel):
    new_username: str
    fullname: str
    email: str
    mobileno: Optional[str] = None
    status: str
    modules: Optional[str] = None
    role: str

class LoginRequest(BaseModel):
    username: str
    password: str
    
class ChangePasswordRequest(BaseModel):
    username: str
    old_password: str
    new_password: str
    
# API 1: Save uploaded Excel to server
@app.post("/save-excel")
async def save_excel(file: UploadFile = File(...)):
    try:
        os.makedirs(EXCEL_SAVE_DIR, exist_ok=True)
        file_path = os.path.join(EXCEL_SAVE_DIR, file.filename)

        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        return {"message": "Excel file saved", "path": file_path}
    except Exception as e:
        logger.exception("Failed to save Excel")
        raise HTTPException(status_code=500, detail="Failed to save Excel")

# API 2: List all Excel files
@app.get("/read-excel")
async def read_all_html_excels():
    try:
        if not os.path.exists(EXCEL_SAVE_DIR):
            return []

        results = []

        for file_name in os.listdir(EXCEL_SAVE_DIR):
            if file_name.endswith(".xls"):  # Only handle fake-Excel (HTML)
                file_path = os.path.join(EXCEL_SAVE_DIR, file_name)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        soup = BeautifulSoup(f, "html.parser")
                        table = soup.find("table")
                        if not table:
                            continue

                        headers = [th.get_text(strip=True) for th in table.find_all("th")]
                        rows = []
                        for tr in table.find_all("tr")[1:]:
                            cells = [td.get_text(strip=True) for td in tr.find_all("td")]
                            if cells:
                                row = dict(zip(headers, cells))
                                rows.append(row)

                        results.append({
                            "campaign_name": os.path.splitext(file_name)[0],
                            "records": rows
                        })
                except Exception as e:
                    logger.warning("Failed to parse HTML table in %s: %s", file_name, str(e))

        return results
    except Exception as e:
        logger.exception("Error reading HTML-based Excel files")
        raise HTTPException(status_code=500, detail="Failed to parse Excel file")
        
        
# API 2: List all Excel files
@app.get("/list-excels")
async def list_excels():
    try:
        if not os.path.exists(EXCEL_SAVE_DIR):
            return {"files": []}

        files = [f for f in os.listdir(EXCEL_SAVE_DIR) if f.endswith(".xls")]
        return {"files": files}
    except Exception as e:
        logger.exception("Error listing Excel files: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to list Excel files")

# API 3: Campaign History  
@app.get("/read-excel/{filename}")
async def read_excel(filename: str):
    try:
        file_path = os.path.join(EXCEL_SAVE_DIR, filename)
        if not os.path.exists(file_path) or not filename.endswith(".xls"):
            raise HTTPException(status_code=404, detail="File not found or invalid format")

        with open(file_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
            table = soup.find("table")
            if not table:
                raise HTTPException(status_code=400, detail="No table found in file")

            headers = [th.get_text(strip=True) for th in table.find_all("th")]
            rows = []
            for tr in table.find_all("tr")[1:]:
                cells = [td.get_text(strip=True) for td in tr.find_all("td")]
                if cells:
                    row = dict(zip(headers, cells))
                    rows.append(row)

            result = {
                "campaign_name": os.path.splitext(filename)[0],
                "records": rows
            }

            return result

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception("Error reading HTML-based Excel file: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to parse Excel file")

# API 3: Signup   
@app.post("/signup")
async def signup(user: UserCreate, background_tasks: BackgroundTasks):
    start_time = time.time()
    try:
        # Validate status
        if user.status not in ["active", "inactive"]:
            raise HTTPException(status_code=400, detail="Invalid status. Must be 'active' or 'inactive'.")
        
        # Validate modules
        valid_modules = ["campaign", "callcenter"]
        module_list = [m.strip() for m in user.modules.split(",") if m.strip()]
        if not module_list or not all(m in valid_modules for m in module_list):
            raise HTTPException(status_code=400, detail="Invalid modules. Must include 'campaign' or 'callcenter'.")

        # Validate role
        valid_roles = ["nurse", "doctor", "admin", "client", "Marketing Team", "CallCenter Team"]
        if user.role not in valid_roles:
            raise HTTPException(status_code=400, detail="Invalid role. Must be 'client', 'nurse', 'doctor', or 'admin'.")

        # Generate and hash password
        password = generate_password()
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        # Insert user into database
        db_start = time.time()
        with get_connection() as conn:
            cursor = conn.cursor()

            # Check if username already exists
            cursor.execute("SELECT 1 FROM blueshift_users WHERE username = ?", (user.username,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Username already exists")

            # Insert new user
            cursor.execute("""
                INSERT INTO blueshift_users (username, password_hash, fullname, email, mobileno, status, modules, role)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user.username, hashed, user.fullname, user.email, user.mobileno, user.status, user.modules, user.role))
            conn.commit()
        
        logger.info("Database operation took %.2f seconds", time.time() - db_start)

        # Schedule email sending as a background task
        background_tasks.add_task(send_email, user.email, user.fullname, user.username, password)

        logger.info("Signup completed in %.2f seconds (email scheduled)", time.time() - start_time)

        return {
            "message": "User created successfully",
            "generated_password": password,
            "username": user.username,
            "email": user.email
        }

    except HTTPException as he:
        logger.error("Signup failed: %s", str(he))
        raise he
    except Exception as e:
        logger.exception("Error occurred during signup: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

# API 4: Login   
@app.post("/login")
async def login(request: LoginRequest):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username, password_hash, role FROM blueshift_users WHERE username = ?", (request.username,))
            user = cursor.fetchone()
            if not user:
                raise HTTPException(status_code=401, detail="Invalid username or password")

            stored_hash = user.password_hash.encode()
            if not bcrypt.checkpw(request.password.encode(), stored_hash):
                raise HTTPException(status_code=401, detail="Invalid username or password")

        return {"message": "Login successful", "username": request.username, "role": user.role}

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception("Error during login")
        raise HTTPException(status_code=500, detail="Internal server error")


# API 5: Retrieve all users   
@app.get("/users", response_model=List[User])
async def get_users():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, fullname, email, mobileno, status, modules, role
                FROM blueshift_users
            """)
            users = [
                {
                    "id": row.id,
                    "username": row.username,
                    "fullname": row.fullname,
                    "email": row.email,
                    "mobileno": row.mobileno,
                    "status": row.status,
                    "modules": row.modules,
                    "role": row.role
                }
                for row in cursor.fetchall()
            ]
            return users
    except Exception as e:
        logger.exception("Error fetching users")
        raise HTTPException(status_code=500, detail="Internal server error")


# API 6: Update Users   
@app.put("/users/{username}")
async def update_user(username: str, user: UserUpdate):
    try:
        # Validate status
        if user.status not in ["active", "inactive"]:
            raise HTTPException(status_code=400, detail="Invalid status. Must be 'active' or 'inactive'.")

        # Validate modules if provided
        if user.modules:
            valid_modules = ["campaign", "callcenter"]
            module_list = [m.strip() for m in user.modules.split(",") if m.strip()]
            if not module_list or not all(m in valid_modules for m in module_list):
                raise HTTPException(status_code=400, detail="Invalid modules. Must include 'campaign' or 'callcenter'.")
        else:
            user.modules = ""

        # Validate role
        valid_roles = ["nurse", "doctor", "admin", "client", "Marketing Team", "CallCenter Team"]
        if user.role not in valid_roles:
            raise HTTPException(status_code=400, detail="Invalid role. Must be 'client', 'nurse', 'doctor', or 'admin'.")

        with get_connection() as conn:
            cursor = conn.cursor()

            # Check if user exists and get id
            cursor.execute("SELECT id FROM blueshift_users WHERE username = ?", (username,))
            user_row = cursor.fetchone()
            if not user_row:
                raise HTTPException(status_code=404, detail="User not found")
            user_id = user_row.id

            # Check if new username already exists (if changed)
            if user.new_username != username:
                cursor.execute("SELECT 1 FROM blueshift_users WHERE username = ? AND id != ?", (user.new_username, user_id))
                if cursor.fetchone():
                    raise HTTPException(status_code=400, detail="New username already exists")

            # Update user (exclude password_hash)
            cursor.execute("""
                UPDATE blueshift_users
                SET username = ?, fullname = ?, email = ?, mobileno = ?, status = ?, modules = ?, role = ?
                WHERE id = ?
            """, (user.new_username, user.fullname, user.email, user.mobileno, user.status, user.modules, user.role, user_id))

            conn.commit()

        return {"message": "User updated successfully"}

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception("Error updating user")
        raise HTTPException(status_code=500, detail="Internal server error")

# API 7: Change Password           
@app.post("/change-password")
async def change_password(request: ChangePasswordRequest):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM blueshift_users WHERE username = ?", (request.username,))
            user = cursor.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            stored_hash = user.password_hash.encode()
            if not bcrypt.checkpw(request.old_password.encode(), stored_hash):
                raise HTTPException(status_code=401, detail="Invalid old password")

            # Hash new password
            new_hashed = bcrypt.hashpw(request.new_password.encode(), bcrypt.gensalt()).decode()

            # Update password
            cursor.execute("UPDATE blueshift_users SET password_hash = ? WHERE username = ?", (new_hashed, request.username))
            conn.commit()

        return {"message": "Password updated successfully"}

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception("Error changing password")
        raise HTTPException(status_code=500, detail="Internal server error")


