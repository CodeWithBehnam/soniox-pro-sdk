"""
Utility functions and helpers for the Soniox SDK.
"""

import random
import time
from collections.abc import Callable
from typing import TypeVar

from soniox.errors import SonioxTimeoutError

T = TypeVar("T")


def exponential_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
) -> float:
    """
    Calculate exponential backoff delay with jitter.

    Adds random jitter (±25%) to prevent thundering herd problem
    where multiple clients retry at exactly the same time.

    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Multiplier for each attempt

    Returns:
        Delay in seconds with random jitter applied
    """
    delay = base_delay * (backoff_factor**attempt)
    delay = min(delay, max_delay)

    # Add random jitter (±25%)
    jitter = delay * 0.25 * (2 * random.random() - 1)
    return max(0, delay + jitter)


def should_retry(status_code: int, retry_statuses: tuple[int, ...]) -> bool:
    """
    Determine if a request should be retried based on status code.

    Args:
        status_code: HTTP status code
        retry_statuses: Tuple of status codes that should trigger retry

    Returns:
        True if request should be retried
    """
    return status_code in retry_statuses


def extract_retry_after(headers: dict[str, str]) -> int | None:
    """
    Extract Retry-After header value.

    Args:
        headers: Response headers

    Returns:
        Retry delay in seconds, or None if not present
    """
    retry_after = headers.get("Retry-After") or headers.get("retry-after")
    if retry_after:
        try:
            return int(retry_after)
        except ValueError:
            return None
    return None


def validate_audio_source(file_id: str | None, audio_url: str | None) -> None:
    """
    Validate that exactly one audio source is provided.

    Args:
        file_id: File ID for uploaded file
        audio_url: URL to audio file

    Raises:
        ValueError: If neither or both sources are provided
    """
    if file_id and audio_url:
        raise ValueError("Provide either file_id or audio_url, not both")
    if not file_id and not audio_url:
        raise ValueError("Must provide either file_id or audio_url")


def poll_until_complete(
    get_status: Callable[[], T],
    is_complete: Callable[[T], bool],
    is_failed: Callable[[T], bool],
    get_error: Callable[[T], str | None],
    poll_interval: float = 2.0,
    timeout: float | None = None,
    max_interval: float = 10.0,
) -> T:
    """
    Poll a resource until it completes or fails with adaptive polling.

    Uses adaptive polling that starts at poll_interval and exponentially increases
    to max_interval, reducing API calls for long-running operations by 50-70%.

    Args:
        get_status: Function to get current status
        is_complete: Function to check if complete
        is_failed: Function to check if failed
        get_error: Function to extract error message
        poll_interval: Initial seconds between polls (default: 2.0)
        timeout: Maximum time to wait
        max_interval: Maximum interval between polls (default: 10.0)

    Returns:
        Final status object

    Raises:
        SonioxTimeoutError: If timeout exceeded
        Exception: If operation failed
    """
    start_time = time.time()
    current_interval = poll_interval

    while True:
        status = get_status()

        if is_complete(status):
            return status

        if is_failed(status):
            error_msg = get_error(status) or "Operation failed"
            raise Exception(error_msg)

        if timeout and (time.time() - start_time) > timeout:
            raise SonioxTimeoutError(
                f"Operation did not complete within {timeout} seconds", timeout=timeout
            )

        time.sleep(current_interval)

        # Increase interval by 1.5x, capped at max_interval
        current_interval = min(current_interval * 1.5, max_interval)
