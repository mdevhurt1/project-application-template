"""
Shared metric helpers for issue text. These are plain functions that
take a string (or an Issue, whose text is used) and do no I/O, so every
analysis computes the metrics the same way.
"""

import re
from typing import Optional, Union

from model import Issue

# A fence line: up to 3 spaces of indent, then 3 or more backticks.
_FENCE = re.compile(r'^ {0,3}(`{3,})')

# Issue-form sections whose text counts as the reporter's own prose.
FORM_SECTIONS = ('Description', 'Workarounds')


def _text_of(text: Union[str, Issue, None]) -> Optional[str]:
    if isinstance(text, Issue):
        return text.text
    return text


def code_share(text: Union[str, Issue, None]) -> float:
    """
    Returns the share of `text` that is code, as a number from 0.0 to 1.0.

    Code is the characters inside fenced code blocks (three or more
    backticks). The fence lines themselves are not counted as code, and
    indented code blocks are not counted either. A block closes on a line
    of at least as many backticks as opened it; an unclosed block runs to
    the end of the text. The share is code characters divided by the total
    characters of `text`. Returns 0.0 for None or empty text.
    """
    text = _text_of(text)
    if not text:
        return 0.0

    code_chars = 0
    open_fence = None  # backtick run that opened the current block
    for line in text.splitlines(keepends=True):
        match = _FENCE.match(line)
        if open_fence is None:
            if match:
                open_fence = match.group(1)
        elif match and len(match.group(1)) >= len(open_fence) \
                and line.strip().strip('`') == '':
            open_fence = None
        else:
            code_chars += len(line)
    return code_chars / len(text)


def extract_section(text: Union[str, Issue, None], header: str) -> Optional[str]:
    """
    Returns the text under a `### <header>` heading, up to the next `### `
    heading or the end of the text, with surrounding whitespace stripped.
    The heading must match `header` exactly (ignoring trailing spaces).
    Returns None if the heading isn't there, and '' if the section is empty.
    """
    text = _text_of(text)
    if not text:
        return None

    lines = text.splitlines()
    for start, line in enumerate(lines):
        if line.rstrip() == f'### {header}':
            break
    else:
        return None

    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith('### '):
            end = i
            break
    return '\n'.join(lines[start + 1:end]).strip()


def form_sections_text(text: Union[str, Issue, None]) -> Optional[str]:
    """
    Returns the Description and Workarounds sections of an issue written
    with the new issue form, joined by a blank line. Sections that are
    missing are left out. Returns None when the issue has neither heading,
    which means it used the old checkbox template.
    """
    sections = [extract_section(text, h) for h in FORM_SECTIONS]
    sections = [s for s in sections if s is not None]
    if not sections:
        return None
    return '\n\n'.join(sections)
