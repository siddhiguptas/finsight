import hashlib
import re


def compute_content_hash(title: str, body: str) -> str:
    normalized = re.sub(r"\s+", " ", (title + body[:200]).lower().strip())
    normalized = re.sub(r"[^a-z0-9 ]", "", normalized)
    return hashlib.sha256(normalized.encode()).hexdigest()

async def is_duplicate(hash_str: str, redis_client, db=None) -> bool:
    # Step 1: Check Redis
    if await redis_client.get(f"dedup:hash:{hash_str}"):
        return True
    
    # Optional: Step 2: Check DB (omitted here as it's handled in the task logic for now)
    return False

