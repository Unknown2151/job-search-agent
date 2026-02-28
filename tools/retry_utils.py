"""
Retry utilities for resilient network operations.
Provides exponential backoff and configurable retry policies.
"""
import asyncio
import logging
import time
from functools import wraps
from typing import Callable, TypeVar, Optional, Any

logger = logging.getLogger(__name__)

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        """
        Initialize retry configuration.

        Args:
            max_attempts: Maximum number of attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay between retries
            exponential_base: Base for exponential backoff calculation
            jitter: Whether to add random jitter to delays
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        delay = self.initial_delay * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_delay)

        if self.jitter:
            import random
            delay = delay * (0.5 + random.random())

        return delay


def retry_sync(
    config: Optional[RetryConfig] = None,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None
) -> Callable[[F], F]:
    """
    Decorator for synchronous function retry with exponential backoff.

    Args:
        config: RetryConfig instance
        exceptions: Tuple of exceptions to catch and retry on
        on_retry: Callback function called on each retry

    Example:
        @retry_sync(RetryConfig(max_attempts=3))
        def get_data():
            ...
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(1, config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < config.max_attempts:
                        delay = config.get_delay(attempt)
                        logger.warning(
                            f"Attempt {attempt}/{config.max_attempts} for {func.__name__} failed: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        if on_retry:
                            on_retry(attempt, e, delay)
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {config.max_attempts} attempts for {func.__name__} failed. "
                            f"Last error: {e}"
                        )

            raise last_exception or Exception(f"Function {func.__name__} failed after {config.max_attempts} attempts")

        return wrapper  # type: ignore
    return decorator


def retry_async(
    config: Optional[RetryConfig] = None,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None
) -> Callable[[F], F]:
    """
    Decorator for asynchronous function retry with exponential backoff.

    Args:
        config: RetryConfig instance
        exceptions: Tuple of exceptions to catch and retry on
        on_retry: Callback function called on each retry

    Example:
        @retry_async(RetryConfig(max_attempts=3))
        async def fetch_data():
            ...
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(1, config.max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < config.max_attempts:
                        delay = config.get_delay(attempt)
                        logger.warning(
                            f"Attempt {attempt}/{config.max_attempts} for {func.__name__} failed: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        if on_retry:
                            on_retry(attempt, e, delay)
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {config.max_attempts} attempts for {func.__name__} failed. "
                            f"Last error: {e}"
                        )

            raise last_exception or Exception(f"Function {func.__name__} failed after {config.max_attempts} attempts")

        return wrapper  # type: ignore
    return decorator
