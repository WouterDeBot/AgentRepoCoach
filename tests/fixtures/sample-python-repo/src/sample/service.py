"""Sample service demonstrating good error messages."""
from __future__ import annotations


class SampleError(Exception):
    """Base class for all Sample-domain exceptions."""


class SampleValidationError(SampleError):
    """Raised when user input fails validation."""


class SampleService:
    """Sample service used for fixture tests."""

    def do_work(self, input_value: int) -> int:
        """Run the sample operation.

        Raises SampleValidationError when the input is out of range.
        """
        if input_value < 0:
            raise SampleValidationError(
                f"Input must be >= 0 but was {input_value}. "
                "Suggested fix: pass a positive integer."
            )
        if input_value > 1000:
            raise SampleValidationError(
                f"Input {input_value} exceeds max. Try a value under 1000."
            )
        return input_value * 2


def _internal_helper() -> int:
    """Module-private helper."""
    return 42
