import re
from datetime import datetime
from typing import Dict, Iterator, List, Optional, Set, Tuple

from data_loader import DataLoader
from model import Issue
from report import print_intro, print_table
import config

# Example issue shown in the usage message when --issue isn't given.
EXAMPLE_ISSUE = 9191

# #1234, but not an HTML entity like &#123;, a reference into another
# repo like owner/repo#12, or a number glued to a word. A full
# issue python-poetry/poetry#1234 reference does count.
_HASH_REF = re.compile(r'(?:(?<![&\w])|(?<=python-poetry/poetry))#(\d+)\b')

# Links to an issue page, e.g. github.com/python-poetry/poetry/issues/1234.
_URL_REF = re.compile(r'github\.com/python-poetry/poetry/issues/(\d+)\b')

# How a related issue is linked to the target issue.
OUTGOING = 'outgoing'
INCOMING = 'incoming'
BOTH = 'both'


def reference_texts(issue:Issue) -> Iterator[Tuple[Optional[datetime], str]]:
    """
    Yields the texts of an issue that can hold references, with the date
    each was written: the title and body (the issue's creation date) and
    every commented event's comment (the event's date).
    """
    for text in (issue.title, issue.text):
        if text:
            yield issue.created_date, text
    for event in issue.events:
        if event.event_type == 'commented' and event.comment:
            yield event.event_date, event.comment


def find_references(text:str) -> Set[int]:
    """
    Returns the issue numbers referenced in text as #1234 or as a link
    to github.com/python-poetry/poetry/issues/1234.
    """
    return {int(n) for pattern in (_HASH_REF, _URL_REF) for n in pattern.findall(text)}


def extract_references(issue:Issue) -> Set[int]:
    """
    Returns the issue numbers referenced in the issue's title, body and
    comments, without the issue's own number.
    """
    refs = set()
    for _, text in reference_texts(issue):
        refs |= find_references(text)
    refs.discard(issue.number)
    return refs


def reference_map(issues:List[Issue]) -> Dict[int, Set[int]]:
    """
    Returns, for every issue, the numbers of the other issues in issues
    it references. References to numbers outside the dataset are dropped.
    """
    known = {i.number for i in issues}
    return {i.number: extract_references(i) & known for i in issues}


def invert(refs:Dict[int, Set[int]]) -> Dict[int, Set[int]]:
    """
    Turns a map of outgoing references into a map of incoming ones: for
    every issue, the numbers of the issues that reference it.
    """
    incoming:Dict[int, Set[int]] = {n: set() for n in refs}
    for source, targets in refs.items():
        for target in targets:
            incoming.setdefault(target, set()).add(source)
    return incoming


def related_issues(number:int, outgoing:Dict[int, Set[int]],
                   incoming:Dict[int, Set[int]]) -> Dict[int, str]:
    """
    Returns the issues related to issue number, each mapped to whether
    the link is OUTGOING (the target references it), INCOMING (it
    references the target) or BOTH.
    """
    out, inc = outgoing.get(number, set()), incoming.get(number, set())
    return {n: BOTH if n in out and n in inc else OUTGOING if n in out else INCOMING
            for n in out | inc}


class RelatedIssuesAnalysis:
    """
    Given an issue, which issues are related to it through references or
    discussion, and how do they compare?
    """

    def __init__(self):
        """
        Constructor
        """
        # Parameter is passed in via command line (--issue)
        self.ISSUE:int = config.get_parameter('issue')

    def run(self):
        """
        Starting point for this analysis.
        """
        if self.ISSUE is None:
            print('Feature 3 needs an issue number. Usage:')
            print(f'  python run.py --feature 3 --issue <number>')
            print(f'For example: python run.py --feature 3 --issue {EXAMPLE_ISSUE}')
            return

        issues:List[Issue] = DataLoader().get_issues()
        by_number = {i.number: i for i in issues}
        target = by_number.get(self.ISSUE)
        if target is None:
            print(f'Issue {self.ISSUE} not found')
            return

        outgoing = reference_map(issues)
        incoming = invert(outgoing)
        related = related_issues(target.number, outgoing, incoming)

        print_intro('RelatedIssuesAnalysis',
                    question=f'Which issues are related to issue #{target.number} through '
                             f'references or discussion, and how do they compare?',
                    method='An issue is related when either issue references the other as '
                           '#N or as a github.com/python-poetry/poetry/issues/N link in its '
                           'title, body or comments. Outgoing means the target references it, '
                           'incoming means it references the target. Numbers that are not in '
                           'the dataset (mostly pull requests) are left out.')

        print(f'Issue #{target.number}: {target.title}')
        if not related:
            print(f'No issues in the dataset reference issue #{target.number}, and it '
                  f'references none of them.')
            return

        counts = {d: sum(1 for v in related.values() if v == d)
                  for d in (OUTGOING, INCOMING, BOTH)}
        print(f'Found {len(related)} related issues: {counts[OUTGOING]} outgoing, '
              f'{counts[INCOMING]} incoming, {counts[BOTH]} both.\n')
        print_table(['issue', 'link', 'state', 'title'],
                    [[f'#{n}', related[n], by_number[n].state.value, by_number[n].title]
                     for n in sorted(related)])


if __name__ == '__main__':
    # Invoke run method when running this module directly
    RelatedIssuesAnalysis().run()
