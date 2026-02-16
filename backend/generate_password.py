"""
Password Hash Generator for Nana AI
Run this script to generate a secure password hash for your .env file
"""

import sys
sys.path.insert(0, '.')

from auth import generate_password_hash

if __name__ == "__main__":
    print("=" * 50)
    print("Nana AI Password Hash Generator")
    print("=" * 50)
    
    password = input("\nEnter your desired password: ")
    
    if len(password) < 8:
        print("⚠️  WARNING: Password should be at least 8 characters long!")
    
    password_hash = generate_password_hash(password)
    
    print("\n✅ Password hash generated successfully!")
    print("\nAdd this line to your backend/.env file:")
    print(f"\nNANA_PASSWORD_HASH={password_hash}")
    print("\n" + "=" * 50)
