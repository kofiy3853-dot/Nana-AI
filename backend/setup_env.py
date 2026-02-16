import sys
import secrets
import os
from pathlib import Path

# Add current directory to path to import auth
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth import generate_password_hash

def setup_env():
    env_path = Path('.env')
    
    # Generate credentials
    password_hash = generate_password_hash("admin123")
    jwt_secret = secrets.token_urlsafe(32)
    
    print(f"Generated Hash for 'admin123': {password_hash}")
    print(f"Generated JWT Secret: {jwt_secret}")
    
    # Read existing .env
    if env_path.exists():
        content = env_path.read_text(encoding='utf-8')
    else:
        content = ""
    
    lines = content.splitlines()
    new_lines = []
    
    has_jwt = False
    has_pwd = False
    has_user = False
    has_origins = False
    
    for line in lines:
        if line.startswith("JWT_SECRET_KEY="):
            new_lines.append(f"JWT_SECRET_KEY={jwt_secret}")
            has_jwt = True
        elif line.startswith("NANA_PASSWORD_HASH="):
            new_lines.append(f"NANA_PASSWORD_HASH={password_hash}")
            has_pwd = True
        elif line.startswith("NANA_USERNAME="):
            new_lines.append("NANA_USERNAME=admin")
            has_user = True
        elif line.startswith("ALLOWED_ORIGINS="):
            # Production origins
            new_lines.append("ALLOWED_ORIGINS=http://localhost:5173,https://nana-ai.vercel.app")
            has_origins = True
        else:
            new_lines.append(line)
            
    # Append missing keys
    if not has_jwt:
        new_lines.append(f"JWT_SECRET_KEY={jwt_secret}")
    if not has_pwd:
        new_lines.append(f"NANA_PASSWORD_HASH={password_hash}")
    if not has_user:
        new_lines.append("NANA_USERNAME=admin")
    if not has_origins:
        new_lines.append("ALLOWED_ORIGINS=http://localhost:5173,https://nana-ai.vercel.app")
        
    # Write back
    env_path.write_text("\n".join(new_lines), encoding='utf-8')
    print("✅ updated .env successfully")

if __name__ == "__main__":
    setup_env()
