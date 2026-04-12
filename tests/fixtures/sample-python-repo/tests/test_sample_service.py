"""Tests for the sample service fixture."""
from sample.service import SampleService, SampleValidationError


def test_do_work_positive_returns_double():
    service = SampleService()
    assert service.do_work(5) == 10


def test_do_work_negative_raises_validation_error():
    service = SampleService()
    try:
        service.do_work(-1)
    except SampleValidationError:
        return
    raise AssertionError("expected SampleValidationError")


def test_do_work_over_max_raises_validation_error():
    service = SampleService()
    try:
        service.do_work(5000)
    except SampleValidationError:
        return
    raise AssertionError("expected SampleValidationError")
