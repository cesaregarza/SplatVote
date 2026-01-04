"""Fingerprint validation and IP hashing service."""

import hashlib
import os
import time
from typing import Optional

import redis
from fastapi import Request


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, respecting proxy headers."""
    # Check X-Forwarded-For header (set by nginx/load balancers)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP (original client)
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct client IP
    if request.client:
        return request.client.host

    return "unknown"


def hash_ip(ip: str) -> str:
    """Hash IP address with server-side pepper for privacy."""
    pepper = os.getenv("VOTE_IP_PEPPER")
    if not pepper:
        raise RuntimeError(
            "VOTE_IP_PEPPER environment variable is required for security. "
            "Set it to a strong random string."
        )
    return hashlib.sha256((pepper + ip).encode()).hexdigest()


def validate_fingerprint(fingerprint: str) -> bool:
    """Validate fingerprint format (SHA-256 hex string)."""
    if len(fingerprint) != 64:
        return False
    try:
        int(fingerprint, 16)
        return True
    except ValueError:
        return False


def get_vote_identity(request: Request, fingerprint: str) -> tuple[str, str]:
    """Return (fingerprint_hash, ip_hash) for vote deduplication."""
    ip = get_client_ip(request)
    ip_hash = hash_ip(ip)
    # Fingerprint is already hashed client-side, use as-is
    return (fingerprint, ip_hash)


class AntiManipulationService:
    """Service for detecting suspicious voting patterns."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.max_fingerprints_per_ip = int(
            os.getenv("MAX_FINGERPRINTS_PER_IP", "5")
        )
        self.max_ips_per_fingerprint = int(
            os.getenv("MAX_IPS_PER_FINGERPRINT", "3")
        )
        self.fingerprint_window_seconds = 3600  # 1 hour
        self.ip_window_seconds = 86400  # 24 hours

    def check_suspicious_patterns(
        self, ip_hash: str, fingerprint: str
    ) -> tuple[bool, Optional[str]]:
        """
        Check for suspicious voting patterns.
        Returns (is_suspicious, reason) tuple.
        """
        try:
            # Check 1: Same IP, multiple fingerprints in short time
            ip_fingerprints_key = f"vote:anti:ip:{ip_hash}:fps"
            self.redis.sadd(ip_fingerprints_key, fingerprint)
            self.redis.expire(ip_fingerprints_key, self.fingerprint_window_seconds)

            unique_fps = self.redis.scard(ip_fingerprints_key)
            if unique_fps and unique_fps > self.max_fingerprints_per_ip:
                return (True, "Too many different devices from same IP")

            # Check 2: Fingerprint appeared from too many IPs
            fp_ips_key = f"vote:anti:fp:{fingerprint}:ips"
            self.redis.sadd(fp_ips_key, ip_hash)
            self.redis.expire(fp_ips_key, self.ip_window_seconds)

            unique_ips = self.redis.scard(fp_ips_key)
            if unique_ips and unique_ips > self.max_ips_per_fingerprint:
                return (True, "Device seen from too many different IPs")

            return (False, None)

        except redis.RedisError:
            # Fail open - allow vote if Redis is unavailable
            return (False, None)

    def record_vote_attempt(
        self,
        ip_hash: str,
        fingerprint: str,
        category_id: int,
        success: bool,
    ) -> None:
        """Record vote attempt for pattern analysis."""
        try:
            timestamp = int(time.time())
            key = f"vote:attempts:{timestamp // 3600}"  # Hourly buckets
            self.redis.hincrby(key, f"{ip_hash}:{fingerprint}:{category_id}:{success}", 1)
            self.redis.expire(key, 86400 * 7)  # Keep for 7 days
        except redis.RedisError:
            pass  # Non-critical, fail silently
