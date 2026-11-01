"""
Shared metric helpers for issue text and lifecycles. These are plain
functions that take a string or Issue objects (or values derived from
them) and do no I/O, so every analysis computes the metrics the same way.
"""

import re
import statistics
from datetime import datetime, timedelta
from typing import Iterable, List, Optional, Set, Union

from model import Event, Issue, State

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


DUPLICATE_LABEL = 'status/duplicate'
NEEDS_REPRODUCTION_LABEL = 'status/needs-reproduction'


def _last_close_event(issue: Issue) -> Optional[Event]:
    """
    Returns the latest dated `closed` event of a closed issue, or None if
    the issue is open or has no dated `closed` event. Ties on date go to
    the event that appears later in the list.
    """
    if issue.state != State.closed:
        return None
    closes = [(e.event_date, i, e) for i, e in enumerate(issue.events)
              if e.event_type == 'closed' and e.event_date is not None]
    if not closes:
        return None
    return max(closes, key=lambda c: (c[0], c[1]))[2]


def close_date(issue: Issue) -> Optional[datetime]:
    """
    Returns the date an issue was closed. For an issue closed more than
    once (reopened), this is the last `closed` event. Returns None for open
    issues and for closed issues with no dated `closed` event; those are
    skipped rather than falling back to `updated_date`.
    """
    event = _last_close_event(issue)
    return event.event_date if event is not None else None


def time_to_close(issue: Issue) -> Optional[timedelta]:
    """
    Returns the time from an issue's creation to its close date (see
    `close_date`). Returns None if either date is missing.
    """
    closed = close_date(issue)
    if closed is None or issue.created_date is None:
        return None
    return closed - issue.created_date


def has_label(issue: Issue, label: str) -> bool:
    """
    Returns whether the issue currently carries `label`.
    """
    return label in (issue.labels or [])


def is_duplicate(issue: Issue) -> bool:
    """
    Returns whether the issue is labeled `status/duplicate`. The
    `marked_as_duplicate` event is not counted.
    """
    return has_label(issue, DUPLICATE_LABEL)


def needs_reproduction(issue: Issue) -> bool:
    """
    Returns whether the issue is labeled `status/needs-reproduction`.
    """
    return has_label(issue, NEEDS_REPRODUCTION_LABEL)


def comment_count(issue: Issue) -> int:
    """
    Returns the number of `commented` events on the issue.
    """
    return sum(1 for e in issue.events if e.event_type == 'commented')


def find_maintainers(issues: Iterable[Issue]) -> Set[str]:
    """
    Returns everyone who added a label to (`labeled` event), or closed
    (`closed` event), an issue they didn't create. Needs the full list of
    issues, so compute it once and pass the result to `closer_type`.
    """
    maintainers = set()
    for issue in issues:
        for e in issue.events:
            if e.event_type in ('labeled', 'closed') \
                    and e.author is not None and e.author != issue.creator:
                maintainers.add(e.author)
    return maintainers


def closer_type(issue: Issue, maintainers: Set[str]) -> Optional[str]:
    """
    Returns who closed the issue, using the same `closed` event as
    `close_date`: 'reporter' if it was the issue's creator, 'maintainer' if
    the closer is in `maintainers` (from `find_maintainers`), and 'other'
    otherwise. Reporter wins when a maintainer closes their own issue.
    Returns None when the issue has no close date.
    """
    event = _last_close_event(issue)
    if event is None:
        return None
    if event.author is not None and event.author == issue.creator:
        return 'reporter'
    if event.author in maintainers:
        return 'maintainer'
    return 'other'


def median_days(timedeltas: Iterable[Optional[timedelta]]) -> Optional[float]:
    """
    Returns the median of `timedeltas` in days, skipping None values.
    Returns None if nothing is left.
    """
    days: List[float] = [td.total_seconds() / 86400
                         for td in timedeltas if td is not None]
    if not days:
        return None
    return statistics.median(days)


def rate(bools: Iterable[Optional[bool]]) -> Optional[float]:
    """
    Returns the share of True values, from 0.0 to 1.0, skipping None
    values. Returns None if nothing is left.
    """
    values = [b for b in bools if b is not None]
    if not values:
        return None
    return sum(1 for b in values if b) / len(values)
