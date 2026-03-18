import re
from html import unescape

from bs4 import BeautifulSoup


def normalize_text(raw_text: str) -> str:
    text = BeautifulSoup(unescape(raw_text or ""), "html.parser").get_text(" ")
    return re.sub(r"\s+", " ", text).strip()
