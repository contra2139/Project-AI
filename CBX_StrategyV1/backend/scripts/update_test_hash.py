import os
import re
import sys

# Add the current directory to sys.path to import app modules
sys.path.append(os.getcwd())

from app.utils.security import hash_password

auth_file = "app/api/v1/auth.py"
if not os.path.exists(auth_file):
    print(f"Error: {auth_file} not found")
    sys.exit(1)

with open(auth_file, "r") as f:
    content = f.read()

new_hash = hash_password("password")
# Replace the ADMIN_PASSWORD_HASH line
content = re.sub(r'ADMIN_PASSWORD_HASH = .*', f'ADMIN_PASSWORD_HASH = "{new_hash}"', content)

with open(auth_file, "w") as f:
    f.write(content)

print(f"Updated auth.py with new hash: {new_hash}")
