"""Tests for calculator operations."""

import pytest

from calculator import ops


class TestAdd:
    def test_add_positive(self):
        assert ops.add(2, 3) == 5

    def test_add_negative(self):
        assert ops.add(-1, -2) == -3

    def test_add_mixed(self):
        assert ops.add(-1, 5) == 4


class TestSubtract:
    def test_subtract_positive(self):
        assert ops.subtract(5, 3) == 2

    def test_subtract_negative(self):
        assert ops.subtract(-1, -2) == 1


class TestMultiply:
    def test_multiply_positive(self):
        assert ops.multiply(3, 4) == 12

    def test_multiply_by_zero(self):
        assert ops.multiply(5, 0) == 0


class TestDivide:
    def test_divide_positive(self):
        assert ops.divide(10, 2) == 5

    def test_divide_float_result(self):
        assert ops.divide(7, 2) == 3.5

    # NOTE: No test for division by zero - this is intentional!
    # The agent should add this test when fixing the bug.
