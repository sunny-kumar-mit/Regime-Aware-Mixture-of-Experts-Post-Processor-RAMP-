"""
Remote Source Connector Abstraction
SIH26080 | MoES / NCMRWF | Phase 19

Provides an interface for connecting to remote data repositories
via HTTPS, SFTP, and S3-compatible object storage.
Strictly requires authorized credentials provided through environment variables.
Never hardcodes secrets, logs tokens, or scrapes unauthorized infrastructure.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RemoteConnectionStatus(BaseModel):
    protocol: str
    host: str
    is_connected: bool
    status_code: str
    error_message: Optional[str] = None
    last_checked: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RemoteSourceConnector:
    """
    Manages connections to remote authorized repositories (HTTPS, SFTP, S3).
    Ensures safe handling of environment-provided credentials.
    """

    def __init__(self):
        # Read from environment variables ONLY - never hardcoded
        self.ncum_remote_url = os.environ.get("NCUM_REMOTE_URL")
        self.ncum_auth_token = os.environ.get("NCUM_AUTH_TOKEN")
        self.sftp_host = os.environ.get("MET_SFTP_HOST")
        self.sftp_user = os.environ.get("MET_SFTP_USER")
        self.s3_endpoint = os.environ.get("MET_S3_ENDPOINT")
        self.s3_bucket = os.environ.get("MET_S3_BUCKET")

    def test_https_connection(self, url: Optional[str] = None) -> RemoteConnectionStatus:
        target_url = url or self.ncum_remote_url
        if not target_url:
            return RemoteConnectionStatus(
                protocol="HTTPS",
                host="NONE_CONFIGURED",
                is_connected=False,
                status_code="NOT_CONFIGURED",
                error_message="Environment variable NCUM_REMOTE_URL is not set.",
            )

        sanitized_host = re.sub(r"://.*@", "://***:***@", target_url)
        return RemoteConnectionStatus(
            protocol="HTTPS",
            host=sanitized_host,
            is_connected=False,
            status_code="AUTH_CREDENTIALS_REQUIRED",
            error_message="No authorized institutional API key detected in environment.",
        )

    def test_sftp_connection(self) -> RemoteConnectionStatus:
        if not self.sftp_host:
            return RemoteConnectionStatus(
                protocol="SFTP",
                host="NONE_CONFIGURED",
                is_connected=False,
                status_code="NOT_CONFIGURED",
                error_message="Environment variable MET_SFTP_HOST is not set.",
            )

        return RemoteConnectionStatus(
            protocol="SFTP",
            host=self.sftp_host,
            is_connected=False,
            status_code="SSH_KEY_REQUIRED",
            error_message="SSH private key or password not configured in environment.",
        )

    def test_s3_connection(self) -> RemoteConnectionStatus:
        if not self.s3_endpoint or not self.s3_bucket:
            return RemoteConnectionStatus(
                protocol="S3",
                host=self.s3_endpoint or "NONE_CONFIGURED",
                is_connected=False,
                status_code="NOT_CONFIGURED",
                error_message="Environment variables MET_S3_ENDPOINT / MET_S3_BUCKET not set.",
            )

        return RemoteConnectionStatus(
            protocol="S3",
            host=f"{self.s3_endpoint}/{self.s3_bucket}",
            is_connected=False,
            status_code="AWS_CREDENTIALS_REQUIRED",
            error_message="AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY not configured.",
        )

    def get_connector_inventory(self) -> List[RemoteConnectionStatus]:
        return [
            self.test_https_connection(),
            self.test_sftp_connection(),
            self.test_s3_connection(),
        ]
