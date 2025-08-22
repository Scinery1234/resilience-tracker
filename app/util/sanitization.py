"""Sanitisation helpers.

This module provides simple utilities to strip potentially unsafe
HTML tags from user-supplied text fields and to trim whitespace.
Use these functions before storing free-form comments or notes in
the database to reduce the risk of XSS if those values are ever
rendered in a web context.
"""
import re

TAG_RE = re.compile(r"<[^>]+>")


def strip_tags(text: str) -> str:
    """Remove HTML tags from the given string.

    Parameters
    ----------
    text: str
        The input string that may contain HTML tags.

    Returns
    -------
    str
        The cleaned string with tags removed and whitespace trimmed.
    """
    if not text:
        return ""
    no_tags = TAG_RE.sub("", text)
    return no_tags.strip()