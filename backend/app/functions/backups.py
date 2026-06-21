import asyncio
import os
import subprocess
from datetime import datetime

from sqlalchemy.engine import make_url

from ..config import settings
from ..database import get_db_session
from ..database.models import PasswordResetToken


def local_backup(backups_dir: str = "./data/backups") -> str:
    """Create a local pg_dump backup of the PostgreSQL database."""
    os.makedirs(backups_dir, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    dest = os.path.join(backups_dir, f"service-{ts}.dump")

    url = make_url(settings.database_url)
    pg_url = url.set(drivername="postgresql")
    connection_uri = pg_url.render_as_string(hide_password=False)

    env = os.environ.copy()
    if pg_url.password:
        env.setdefault("PGPASSWORD", pg_url.password)

    cmd = [
        "pg_dump",
        f"--dbname={connection_uri}",
        "-Fc",
        f"--file={dest}",
    ]

    subprocess.run(cmd, check=True, env=env, timeout=60 * 15)
    return dest


def upload_to_r2(filepath: str):
    """Upload backup to Cloudflare R2"""
    if not settings.enable_r2_backup:
        return
        
    try:
        import boto3
        s3 = boto3.client(
            "s3",
            endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
        )
        
        key = os.path.basename(filepath)
        with open(filepath, "rb") as f:
            s3.upload_fileobj(f, settings.r2_bucket, key)
    except Exception as e:
        print(f"R2 backup failed: {e}")


async def daily_backup_loop():
    """Run daily backups"""
    while True:
        try:
            backup_path = await asyncio.to_thread(local_backup)
            print(f"Created backup: {backup_path}")
            await asyncio.to_thread(upload_to_r2, backup_path)
        except Exception as e:
            print(f"Backup failed: {e}")
        
        await asyncio.sleep(60 * 60 * 24)  # 24 hours


async def cleanup_expired_tokens():
    """Clean up expired password reset tokens"""
    while True:
        try:
            count = await asyncio.to_thread(_cleanup_expired_tokens_once)
            if count > 0:
                print(f"Cleaned up {count} expired tokens")
        except Exception as e:
            print(f"Token cleanup failed: {e}")
        
        await asyncio.sleep(3600)  # 1 hour


def _cleanup_expired_tokens_once() -> int:
    with get_db_session() as db:
        expired = db.query(PasswordResetToken).filter(
            PasswordResetToken.expires_at < datetime.utcnow(),
            PasswordResetToken.active == True,
        )
        count = expired.update({"active": False})
        db.commit()
        return count
