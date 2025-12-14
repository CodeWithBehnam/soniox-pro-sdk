"""
Synchronous HTTP client for the Soniox API.

This module provides the main client class for interacting with the Soniox
REST API in a synchronous manner.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional, Union

import httpx
from pydantic import ValidationError

from soniox.config import SonioxConfig
from soniox.errors import (
    SonioxAPIError,
    SonioxAuthenticationError,
    SonioxConnectionError,
    SonioxRateLimitError,
    SonioxTimeoutError,
    SonioxTranscriptionError,
    SonioxValidationError,
)
from soniox.types import (
    CreateTemporaryApiKeyRequest,
    CreateTranscriptionRequest,
    File,
    FileList,
    FileUploadResponse,
    FileUrlResponse,
    Model,
    ModelList,
    TemporaryApiKey,
    Transcription,
    TranscriptionList,
    TranscriptionResult,
    TranscriptionStatus,
)
from soniox.utils import exponential_backoff, extract_retry_after, poll_until_complete, should_retry


class SonioxClient:
    """
    Synchronous client for the Soniox Speech-to-Text API.

    This client provides access to all REST API endpoints including
    file uploads, transcriptions, models, and authentication.

    Example:
        ```python
        from soniox import SonioxClient

        client = SonioxClient(api_key="your-api-key")

        # Upload and transcribe
        file = client.files.upload("audio.mp3")
        transcription = client.transcriptions.create(file_id=file.id)
        result = client.transcriptions.wait_for_completion(transcription.id)
        print(result.transcript.text)
        ```
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[SonioxConfig] = None,
        **config_overrides: Any,
    ) -> None:
        """
        Initialise the Soniox client.

        Args:
            api_key: Soniox API key (can also be set via environment)
            config: Custom configuration object
            **config_overrides: Override specific config values

        Raises:
            ValueError: If API key is not provided or found in environment
        """
        # Set up configuration
        if config is None:
            config = SonioxConfig(api_key=api_key, **config_overrides)
        elif api_key:
            config = config.with_overrides(api_key=api_key, **config_overrides)

        config.validate()
        self.config = config

        # Create HTTP client with connection pooling
        self._client = httpx.Client(
            base_url=self.config.api_base_url,
            timeout=httpx.Timeout(
                connect=self.config.connect_timeout,
                read=self.config.read_timeout,
                write=self.config.write_timeout,
                pool=None,
            ),
            limits=httpx.Limits(
                max_connections=self.config.max_connections,
                max_keepalive_connections=self.config.max_keepalive_connections,
                keepalive_expiry=self.config.keepalive_expiry,
            ),
            headers={
                "User-Agent": "soniox-pro-sdk/1.0.0",
            },
        )

        # Initialise API resource handlers
        self.files = FilesAPI(self)
        self.transcriptions = TranscriptionsAPI(self)
        self.models = ModelsAPI(self)
        self.auth = AuthAPI(self)

    def __enter__(self) -> SonioxClient:
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    def close(self) -> None:
        """Close the HTTP client and release connections."""
        self._client.close()

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        files: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Make an HTTP request with retry logic.

        Args:
            method: HTTP method
            endpoint: API endpoint
            json: JSON request body
            data: Form data
            files: Files to upload
            params: Query parameters
            **kwargs: Additional arguments for httpx

        Returns:
            HTTP response

        Raises:
            SonioxAPIError: For API errors
            SonioxAuthenticationError: For auth errors
            SonioxRateLimitError: When rate limited
            SonioxConnectionError: For connection errors
            SonioxTimeoutError: For timeouts
        """
        url = endpoint if endpoint.startswith("http") else f"/api/v1{endpoint}"
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.config.api_key}"

        for attempt in range(self.config.max_retries + 1):
            try:
                response = self._client.request(
                    method=method,
                    url=url,
                    json=json,
                    data=data,
                    files=files,
                    params=params,
                    headers=headers,
                    **kwargs,
                )

                # Handle successful responses
                if response.status_code < 400:
                    return response

                # Handle error responses
                self._handle_error_response(response)

            except httpx.TimeoutException as e:
                if attempt == self.config.max_retries:
                    raise SonioxTimeoutError(f"Request timed out: {e}") from e
                time.sleep(exponential_backoff(attempt, backoff_factor=self.config.retry_backoff_factor))

            except httpx.ConnectError as e:
                if attempt == self.config.max_retries:
                    raise SonioxConnectionError(f"Failed to connect: {e}") from e
                time.sleep(exponential_backoff(attempt, backoff_factor=self.config.retry_backoff_factor))

            except httpx.HTTPError as e:
                raise SonioxConnectionError(f"HTTP error occurred: {e}") from e

        # Should never reach here
        raise SonioxAPIError("Maximum retries exceeded")

    def _handle_error_response(self, response: httpx.Response) -> None:
        """
        Handle error responses from the API.

        Args:
            response: HTTP response

        Raises:
            Appropriate SonioxError subclass
        """
        try:
            error_data = response.json()
            error_message = error_data.get("error_message", response.text)
            error_code = error_data.get("error_code", response.status_code)
        except Exception:
            error_message = response.text or f"HTTP {response.status_code}"
            error_code = response.status_code

        # Authentication errors
        if response.status_code == 401:
            raise SonioxAuthenticationError(
                error_message,
                status_code=response.status_code,
                error_code=str(error_code),
            )

        # Rate limit errors
        if response.status_code == 429:
            retry_after = extract_retry_after(dict(response.headers))
            raise SonioxRateLimitError(
                error_message,
                retry_after=retry_after,
            )

        # Generic API errors
        raise SonioxAPIError(
            error_message,
            status_code=response.status_code,
            error_code=str(error_code),
            response_body=response.text,
        )


class FilesAPI:
    """API methods for managing audio files."""

    def __init__(self, client: SonioxClient) -> None:
        """Initialise FilesAPI with client reference."""
        self.client = client

    def upload(self, file_path: Union[str, Path], name: Optional[str] = None) -> File:
        """
        Upload an audio file.

        Args:
            file_path: Path to audio file
            name: Optional custom name

        Returns:
            Uploaded file object

        Example:
            ```python
            file = client.files.upload("audio.mp3")
            print(f"Uploaded: {file.id}")
            ```
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_name = name or file_path.name

        with open(file_path, "rb") as f:
            files = {"file": (file_name, f)}
            response = self.client._request("POST", "/files", files=files)

        data = response.json()
        return File(**data["file"])

    def list(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> FileList:
        """
        List uploaded files.

        Args:
            limit: Maximum number of files to return
            offset: Number of files to skip

        Returns:
            List of files
        """
        params = {"limit": limit, "offset": offset}
        response = self.client._request("GET", "/files", params=params)
        return FileList(**response.json())

    def get(self, file_id: str) -> File:
        """
        Get file metadata.

        Args:
            file_id: File ID

        Returns:
            File object
        """
        response = self.client._request("GET", f"/files/{file_id}")
        return File(**response.json()["file"])

    def get_url(self, file_id: str) -> FileUrlResponse:
        """
        Get temporary download URL for a file.

        Args:
            file_id: File ID

        Returns:
            Temporary URL and expiration
        """
        response = self.client._request("GET", f"/files/{file_id}/url")
        return FileUrlResponse(**response.json())

    def delete(self, file_id: str) -> None:
        """
        Delete a file.

        Args:
            file_id: File ID
        """
        self.client._request("DELETE", f"/files/{file_id}")


class TranscriptionsAPI:
    """API methods for managing transcriptions."""

    def __init__(self, client: SonioxClient) -> None:
        """Initialise TranscriptionsAPI with client reference."""
        self.client = client

    def create(
        self,
        model: str = "stt-async-v3",
        file_id: Optional[str] = None,
        audio_url: Optional[str] = None,
        **kwargs: Any,
    ) -> Transcription:
        """
        Create a new transcription.

        Args:
            model: Model to use
            file_id: ID of uploaded file
            audio_url: URL to audio file
            **kwargs: Additional transcription options

        Returns:
            Transcription object

        Example:
            ```python
            transcription = client.transcriptions.create(
                file_id=file.id,
                enable_speaker_diarization=True,
            )
            ```
        """
        try:
            request = CreateTranscriptionRequest(
                model=model,
                file_id=file_id,
                audio_url=audio_url,
                **kwargs,
            )
        except ValidationError as e:
            raise SonioxValidationError(f"Invalid transcription request: {e}") from e

        request_dict = request.model_dump(exclude_none=True)
        response = self.client._request("POST", "/transcriptions", json=request_dict)
        return Transcription(**response.json()["transcription"])

    def get(self, transcription_id: str) -> Transcription:
        """
        Get transcription status.

        Args:
            transcription_id: Transcription ID

        Returns:
            Transcription object
        """
        response = self.client._request("GET", f"/transcriptions/{transcription_id}")
        return Transcription(**response.json()["transcription"])

    def get_result(self, transcription_id: str) -> TranscriptionResult:
        """
        Get complete transcription result including transcript.

        Args:
            transcription_id: Transcription ID

        Returns:
            Transcription result with transcript

        Raises:
            SonioxTranscriptionError: If transcription is not complete
        """
        transcription = self.get(transcription_id)

        if transcription.status != TranscriptionStatus.COMPLETED:
            raise SonioxTranscriptionError(
                f"Transcription not complete: {transcription.status}",
                transcription_id=transcription_id,
            )

        response = self.client._request("GET", f"/transcriptions/{transcription_id}/transcript")
        transcript_data = response.json()

        return TranscriptionResult(
            transcription=transcription,
            transcript=transcript_data.get("transcript"),
        )

    def list(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> TranscriptionList:
        """
        List transcriptions.

        Args:
            limit: Maximum number to return
            offset: Number to skip

        Returns:
            List of transcriptions
        """
        params = {"limit": limit, "offset": offset}
        response = self.client._request("GET", "/transcriptions", params=params)
        return TranscriptionList(**response.json())

    def delete(self, transcription_id: str) -> None:
        """
        Delete a transcription.

        Args:
            transcription_id: Transcription ID
        """
        self.client._request("DELETE", f"/transcriptions/{transcription_id}")

    def wait_for_completion(
        self,
        transcription_id: str,
        poll_interval: float = 2.0,
        timeout: Optional[float] = None,
    ) -> TranscriptionResult:
        """
        Wait for transcription to complete.

        Args:
            transcription_id: Transcription ID
            poll_interval: Seconds between status checks
            timeout: Maximum time to wait

        Returns:
            Complete transcription result

        Example:
            ```python
            result = client.transcriptions.wait_for_completion(
                transcription.id,
                timeout=300,
            )
            print(result.transcript.text)
            ```
        """

        def get_status() -> Transcription:
            return self.get(transcription_id)

        def is_complete(t: Transcription) -> bool:
            return t.status == TranscriptionStatus.COMPLETED

        def is_failed(t: Transcription) -> bool:
            return t.status == TranscriptionStatus.FAILED

        def get_error(t: Transcription) -> Optional[str]:
            return t.error_message

        transcription = poll_until_complete(
            get_status=get_status,
            is_complete=is_complete,
            is_failed=is_failed,
            get_error=get_error,
            poll_interval=poll_interval,
            timeout=timeout,
        )

        return self.get_result(transcription.id)


class ModelsAPI:
    """API methods for querying available models."""

    def __init__(self, client: SonioxClient) -> None:
        """Initialise ModelsAPI with client reference."""
        self.client = client

    def list(self) -> ModelList:
        """
        List available models.

        Returns:
            List of models
        """
        response = self.client._request("GET", "/models")
        return ModelList(**response.json())


class AuthAPI:
    """API methods for authentication."""

    def __init__(self, client: SonioxClient) -> None:
        """Initialise AuthAPI with client reference."""
        self.client = client

    def create_temporary_key(self, duration_seconds: int = 3600) -> TemporaryApiKey:
        """
        Create a temporary API key.

        Args:
            duration_seconds: Key validity duration (60-86400 seconds)

        Returns:
            Temporary API key

        Example:
            ```python
            temp_key = client.auth.create_temporary_key(duration_seconds=1800)
            # Use temp_key.api_key in client-side applications
            ```
        """
        try:
            request = CreateTemporaryApiKeyRequest(duration_seconds=duration_seconds)
        except ValidationError as e:
            raise SonioxValidationError(f"Invalid duration: {e}") from e

        response = self.client._request("POST", "/auth/temporary-keys", json=request.model_dump())
        return TemporaryApiKey(**response.json())
