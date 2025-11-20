import secrets
import os
from cryptography.fernet import Fernet

# Generate secrets
jwt_secret = secrets.token_urlsafe(32)
fernet_key = Fernet.generate_key().decode()

print(f"Generated JWT_SECRET: {jwt_secret}")
print(f"Generated TOKEN_ENCRYPTION_KEY: {fernet_key}")

# Read template
template_path = ".env.template"
env_path = ".env"

if os.path.exists(template_path):
    with open(template_path, "r") as f:
        content = f.read()
    
    # Replace placeholders
    # We assume the template has "JWT_SECRET=" and "TOKEN_ENCRYPTION_KEY="
    # We'll just replace the lines to be safe
    
    lines = content.splitlines()
    new_lines = []
    for line in lines:
        if line.startswith("JWT_SECRET="):
            new_lines.append(f"JWT_SECRET={jwt_secret}")
        elif line.startswith("TOKEN_ENCRYPTION_KEY="):
            new_lines.append(f"TOKEN_ENCRYPTION_KEY={fernet_key}")
        else:
            new_lines.append(line)
            
    new_content = "\n".join(new_lines)
    
    with open(env_path, "w") as f:
        f.write(new_content)
    
    print(f"Successfully wrote to {env_path}")

else:
    print(f"Error: {template_path} not found. Please ensure it exists.")
