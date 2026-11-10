from decimal import Decimal
from app.scraper import parse_price

def test_rupee_price():
    assert parse_price("₹1,23,456.78") == Decimal("123456.78")

def test_rs_price():
    assert parse_price("Rs. 2,499") == Decimal("2499.00")

def test_invalid_price():
    assert parse_price("Price unavailable") is None
