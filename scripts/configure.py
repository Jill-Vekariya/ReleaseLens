"""Create local Compose credentials, refusing to overwrite existing configuration."""

import json
import os
import secrets
from pathlib import Path

path = Path(__file__).resolve().parents[1] / ".env"
credentials = {
    secrets.token_urlsafe(32): {"user": f"local-{role}", "role": role}
    for role in ("reader", "engineer", "admin")
}
content = (
    "DB_PASSWORD="
    + secrets.token_hex(24)
    + "\nRELEASELENS_TOKENS='"
    + json.dumps(credentials)
    + "'\n"
)
with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as file:
    file.write(content)
print("Created local .env credentials. Keep this file private. Next: docker compose up --build")
