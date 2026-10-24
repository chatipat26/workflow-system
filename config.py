import os
from typing import Optional

def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    # 1. Environment variable
    val = os.environ.get(key)
    if val:
        return val.strip()
    
    # 2. Check .env file
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() == key:
                            return v.strip().strip("'\"")
        except Exception:
            pass
            
    # 3. Fallback to .streamlit/secrets.toml
    secrets_file = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
    if os.path.exists(secrets_file):
        try:
            import toml
            data = toml.load(secrets_file)
            if key in data:
                return str(data[key]).strip()
        except Exception:
            pass

    return default

DATABASE_URL = get_secret("DATABASE_URL")
SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")
JWT_SECRET = get_secret("JWT_SECRET", "svv-team-workflow-secret-jwt-key-2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 30
