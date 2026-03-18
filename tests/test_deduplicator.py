import pytest
from app.processing.deduplicator import compute_content_hash, normalize_text

def test_compute_content_hash_same_input():
    text1 = "Apple Reports Record Earnings"
    text2 = "Apple Reports Record Earnings"

    hash1 = compute_content_hash(text1, "Some content here")
    hash2 = compute_content_hash(text2, "Some content here")

    assert hash1 == hash2

def test_compute_content_hash_different_input():
    text1 = "Apple Reports Record Earnings"
    text2 = "Google Reports Record Earnings"

    hash1 = compute_content_hash(text1, "Some content here")
    hash2 = compute_content_hash(text2, "Some content here")

    assert hash1 != hash2

def test_normalize_text():
    text = "  Apple   Reports   Earnings  "
    normalized = normalize_text(text)

    assert normalized == "apple reports earnings"

def test_content_hash_sha256_format():
    text = "Test Title"
    content = "Test Content"

    hash_result = compute_content_hash(text, content)

    assert len(hash_result) == 64
    assert all(c in "0123456789abcdef" for c in hash_result)
