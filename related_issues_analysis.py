import os
import re
from datetime import datetime, timedelta
from typing import Dict, Iterator, List, Optional, Set, Tuple

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from data_loader import DataLoader
from issue_metrics import close_date, find_maintainers, median_days, time_to_close
from model import Issue, State
from report import print_intro, print_table, print_finding
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

CHART_PATH = os.path.join('output', 'f3_related_issues.png')


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


def reference_dates(issue:Issue, numbers:Set[int]) -> List[Optional[datetime]]:
    """
    Returns the date of every title, body or comment of issue that
    references any of numbers, one entry per text. Dates can be None.
    """
    return [date for date, text in reference_texts(issue) if find_references(text) & numbers]


def participants(issue:Issue) -> Set[str]:
    """
    Returns the distinct authors of the issue's comments.
    """
    return {e.author for e in issue.events
            if e.event_type == 'commented' and e.author is not None}


def issue_stats(issue:Issue, dates:List[Optional[datetime]],
                maintainers:Set[str]) -> dict:
    """
    Returns the metrics of one issue in the related set, given the dates
    of the texts that hold its references. Values that can't be
    computed, because the issue is open or a date is missing, are None.
    """
    dated = [d for d in dates if d is not None]
    first_ref = min(dated) if dated else None
    closed = close_date(issue)
    people = participants(issue)
    return {
        'refs': len(dates),
        'first_ref': first_ref,
        'time_to_close': time_to_close(issue),
        'ref_to_close': closed - first_ref if closed is not None and first_ref is not None else None,
        'participants': len(people),
        'insiders': sum(1 for p in people if p == issue.creator or p in maintainers),
    }


def days(td:Optional[timedelta]) -> Optional[float]:
    """
    Returns td in days, or None.
    """
    return td.total_seconds() / 86400 if td is not None else None


def format_days(td:Optional[timedelta], issue:Issue) -> str:
    """
    Formats td in days, or as 'open' or 'n/a' when it is missing.
    """
    if td is None:
        return 'open' if issue.state == State.open else 'n/a'
    return f'{days(td):.1f}'


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
            print_finding(f'No issues in the dataset reference issue #{target.number}, '
                          f'and it references none of them.')
            return

        counts = {d: sum(1 for v in related.values() if v == d)
                  for d in (OUTGOING, INCOMING, BOTH)}
        print(f'Found {len(related)} related issues: {counts[OUTGOING]} outgoing, '
              f'{counts[INCOMING]} incoming, {counts[BOTH]} both.\n')

        maintainers = find_maintainers(issues)
        stats = {n: issue_stats(by_number[n],
                                reference_dates(by_number[n], {target.number})
                                + reference_dates(target, {n}),
                                maintainers)
                 for n in sorted(related)}
        target_stats = issue_stats(target,
                                   reference_dates(target, set(related))
                                   + [d for n in sorted(related)
                                      for d in reference_dates(by_number[n], {target.number})],
                                   maintainers)

        def row(issue:Issue, link:str, s:dict) -> list:
            return [f'#{issue.number}', link, issue.state.value, s['refs'],
                    s['first_ref'].date().isoformat() if s['first_ref'] else 'n/a',
                    format_days(s['time_to_close'], issue),
                    format_days(s['ref_to_close'], issue),
                    s['participants'], s['insiders'], issue.title]

        print_table(['issue', 'link', 'state', 'refs', 'first ref', 'days to close',
                     'ref to close', 'people', 'reporter/maint.', 'title'],
                    [row(target, 'target', target_stats)]
                    + [row(by_number[n], related[n], stats[n]) for n in sorted(related)])
        print('refs: titles, bodies and comments that link the issue and the target '
              '(for the target, all of them). first ref: date of the earliest. '
              'ref to close: days from the first ref to the close, negative when the '
              'reference came after the close. people: distinct commenters; '
              'reporter/maint.: how many of them are the reporter or a maintainer.\n')

        print_finding(self.finding(target, target_stats, related, stats))
        self.plot(target, target_stats, related, stats, by_number)

    def finding(self, target:Issue, target_stats:dict, related:Dict[int, str],
                stats:Dict[int, dict]) -> str:
        """
        Summarizes how the related issues compare to the target.
        """
        closed = [n for n in related if stats[n]['time_to_close'] is not None]
        still_open = sum(1 for n in related if stats[n]['time_to_close'] is None)
        if target_stats['time_to_close'] is not None:
            text = f'Issue #{target.number} closed after {days(target_stats["time_to_close"]):.1f} days. '
        else:
            text = f'Issue #{target.number} has no close date ({format_days(None, target)}). '
        text += f'{len(closed)} of the {len(related)} related issues are closed'
        if closed:
            ttc = median_days(stats[n]['time_to_close'] for n in closed)
            text += f', with a median time to close of {ttc:.1f} days'
            ref_to_close = [stats[n]['ref_to_close'] for n in closed
                            if stats[n]['ref_to_close'] is not None]
            if ref_to_close:
                after = sum(1 for td in ref_to_close if td < timedelta(0))
                text += (f' and a median of {median_days(ref_to_close):.1f} days from the '
                         f'first reference to the close')
                if after:
                    text += f'. {after} of them were first linked only after they had closed'
        text += '.'
        if still_open:
            text += f' The other {still_open} are open or have no close date.'
        return text

    def plot(self, target:Issue, target_stats:dict, related:Dict[int, str],
             stats:Dict[int, dict], by_number:Dict[int, Issue]):
        """
        Plots a timeline with one bar per issue, from creation to close,
        and a marker at its first reference. The target's lifespan is
        shaded behind the bars. Issues still open (or with no close date)
        run to the right edge.
        """
        rows = [(target, 'target', target_stats)] \
            + [(by_number[n], related[n], stats[n]) for n in sorted(related)]
        rows = [r for r in rows if r[0].created_date is not None]
        if not rows:
            print('No issue in the related set has a creation date, so there is no chart.')
            return

        dates = [d for issue, _, s in rows
                 for d in (issue.created_date, close_date(issue), s['first_ref']) if d is not None]
        edge = max(dates) + (max(dates) - min(dates)) * 0.05
        colors = {'target': 'black', OUTGOING: 'tab:blue', INCOMING: 'tab:orange', BOTH: 'tab:green'}

        fig, ax = plt.subplots(figsize=(12, max(3.5, 1.5 + 0.4 * len(rows))))
        closed = close_date(target)
        ax.axvspan(target.created_date, closed or edge, color='grey', alpha=0.15)
        if closed is not None:
            ax.axvline(closed, color='black', linestyle='--', linewidth=1)
        for y, (issue, link, s) in enumerate(rows):
            end = close_date(issue)
            ax.hlines(y, issue.created_date, end or edge, colors=colors[link], linewidth=6,
                      linestyles='solid' if end else 'dotted')
            # Most bars are a day or two long, too short to see, so mark both ends
            ax.plot(issue.created_date, y, marker='o', color=colors[link], markersize=6)
            if end is not None:
                ax.plot(end, y, marker='|', color=colors[link], markersize=12, markeredgewidth=2)
            if s['first_ref'] is not None:
                ax.plot(s['first_ref'], y, marker='D', color='red', markerfacecolor='none',
                        markersize=8, markeredgewidth=1.5)
            ax.annotate(format_days(s['time_to_close'], issue), (end or edge, y),
                        xytext=(6, 0), textcoords='offset points', va='center', fontsize=8)

        ax.set_yticks(range(len(rows)), [f'#{issue.number}' for issue, _, _ in rows])
        ax.invert_yaxis()
        ax.set_xlim(right=edge)
        ax.set_title(f'Issues related to #{target.number}: lifespan and first reference')
        ax.set_xlabel('Date (labels at bar ends: days to close)')
        ax.set_ylabel('Issue')
        handles = [Line2D([], [], color=c, linewidth=6, label=l) for l, c in colors.items()
                   if l == 'target' or l in related.values()]
        handles += [Line2D([], [], color='grey', linewidth=6, linestyle='dotted',
                           label='open or no close date'),
                    Line2D([], [], color='grey', marker='o', linestyle='', label='created'),
                    Line2D([], [], color='grey', marker='|', markersize=12, markeredgewidth=2,
                           linestyle='', label='closed'),
                    Line2D([], [], color='red', marker='D', markerfacecolor='none',
                           markeredgewidth=1.5, linestyle='', label='first reference'),
                    Patch(color='grey', alpha=0.15, label=f'#{target.number} open')]
        if closed is not None:
            handles.append(Line2D([], [], color='black', linestyle='--', linewidth=1,
                                  label=f'#{target.number} closed'))
        ax.legend(handles=handles, loc='upper left', bbox_to_anchor=(1.06, 1))
        fig.autofmt_xdate()
        fig.tight_layout()
        os.makedirs(os.path.dirname(CHART_PATH), exist_ok=True)
        fig.savefig(CHART_PATH, dpi=150)
        print(f'Chart saved to {CHART_PATH}')
        # Agg can't open a window (no GUI toolkit or display), so only show when one can
        if plt.get_backend().lower() != 'agg':
            plt.show()


if __name__ == '__main__':
    # Invoke run method when running this module directly
    RelatedIssuesAnalysis().run()
