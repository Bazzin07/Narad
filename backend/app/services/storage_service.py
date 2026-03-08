"""
Storage Service — swappable backend for raw article storage.
LocalStorage for development, S3Storage for production.
"""
import json
import os
import logging
from datetime import datetime
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


class LocalStorage:
    """Filesystem-based storage for development."""

    def __init__(self, base_path: str = None):
        self.base_path = base_path or settings.local_storage_path
        os.makedirs(self.base_path, exist_ok=True)

    def store(self, key: str, data: dict) -> str:
        """Store data as JSON file. Returns the storage key."""
        filepath = os.path.join(self.base_path, key)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=str)
        logger.info(f"Stored article locally: {key}")
        return key

    def retrieve(self, key: str) -> Optional[dict]:
        """Retrieve stored JSON data by key."""
        filepath = os.path.join(self.base_path, key)
        if not os.path.exists(filepath):
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def exists(self, key: str) -> bool:
        filepath = os.path.join(self.base_path, key)
        return os.path.exists(filepath)


class S3Storage:
    """S3-based storage for production."""

    def __init__(self, bucket: str = None, region: str = None):
        import boto3
        self.bucket = bucket or settings.s3_bucket
        self.region = region or settings.aws_region
        self.s3 = boto3.client("s3", region_name=self.region)

    def store(self, key: str, data: dict) -> str:
        """Store data as JSON in S3. Returns the S3 key."""
        body = json.dumps(data, ensure_ascii=False, default=str)
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=body, ContentType="application/json")
        logger.info(f"Stored article in S3: s3://{self.bucket}/{key}")
        return key

    def retrieve(self, key: str) -> Optional[dict]:
        """Retrieve JSON data from S3."""
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=key)
            return json.loads(response["Body"].read().decode("utf-8"))
        except self.s3.exceptions.NoSuchKey:
            return None

    def exists(self, key: str) -> bool:
        try:
            self.s3.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False


def get_storage():
    """Factory — returns the configured storage backend."""
    if settings.storage_backend == "s3":
        return S3Storage()
    return LocalStorage()
