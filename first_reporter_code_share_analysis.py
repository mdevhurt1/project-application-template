import os
import statistics
from datetime import datetime
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np

from data_loader import DataLoader
from issue_metrics import (closer_type, code_share, comment_count, extract_section,
                           find_maintainers, is_duplicate, median_days,
                           needs_reproduction, rate, time_to_close)
from model import Issue
from report import fmt, print_intro, print_table, print_finding, save_chart
import config

# Label used when --label isn't given.
DEFAULT_LABEL = 'kind/bug'

# Event types that count as a user's own activity. Creating an issue
# also counts. Passive events like `subscribed` and `mentioned` don't.
ACTIVITY_EVENTS = ('commented', 'labeled', 'closed')

# Issue-form section whose code share decides an issue's group.
SECTION = 'Description'

# Non-zero shares at or above this percentile go in the top group.
TOP_PERCENTILE = 90

# Groups in display order.
GROUPS = ('no code', 'middle', 'top 10%')
CLOSERS = ('reporter', 'maintainer', 'other')

# Groups smaller than this get a warning, since their numbers are noisy.
MIN_GROUP_SIZE = 10

# Where the chart is saved, relative to the working directory.
CHART_PATH = os.path.join('output', 'f2_code_share_groups.png')


def first_activity_dates(issues:List[Issue]) -> Dict[str, datetime]:
    """
    Returns each user's earliest activity in the whole dataset: creating an
    issue, or an ACTIVITY_EVENTS event they authored. Issues and events
    without a user or a date are ignored.
    """
    first:Dict[str, datetime] = {}

    def record(user:str, date:datetime):
        if user is None or date is None:
            return
        if user not in first or date < first[user]:
            first[user] = date

    for issue in issues:
        record(issue.creator, issue.created_date)
        for event in issue.events:
            if event.event_type in ACTIVITY_EVENTS:
                record(event.author, event.event_date)
    return first


def is_first_time_reporter(issue:Issue, first_dates:Dict[str, datetime]) -> bool:
    """
    Returns whether the issue's creator had no activity before creating it,
    i.e. their first activity is the issue's own creation date.
    """
    if issue.creator is None or issue.created_date is None:
        return False
    return first_dates.get(issue.creator) == issue.created_date


def top_cutoff(shares:List[float]) -> Optional[float]:
    """
    Returns the TOP_PERCENTILE percentile of the non-zero shares (linear
    interpolation), or None if there are none.
    """
    nonzero = [s for s in shares if s > 0]
    if not nonzero:
        return None
    return float(np.percentile(nonzero, TOP_PERCENTILE))


def share_group(share:float, cutoff:Optional[float]) -> str:
    """
    Returns the group for a code share: 'no code' for 0, 'top 10%' for a
    share at or above `cutoff`, and 'middle' otherwise.
    """
    if share == 0:
        return 'no code'
    if cutoff is not None and share >= cutoff:
        return 'top 10%'
    return 'middle'


class FirstReporterAnalysis:
    """
    Within a chosen label, are issues from first-time reporters resolved
    differently depending on how much of their description is pasted code?
    """

    def __init__(self):
        """
        Constructor
        """
        # Parameter is passed in via command line (--label)
        self.LABEL:str = config.get_parameter('label')

    def run(self):
        """
        Starting point for this analysis.
        """
        issues:List[Issue] = DataLoader().get_issues()

        label = self.LABEL
        if label is None:
            label = DEFAULT_LABEL
            print(f'No --label given, using the default `{label}`.')

        available = sorted({l for issue in issues for l in issue.labels})
        if label not in available:
            print(f'Label `{label}` was not found in the data. Available labels:')
            for l in available:
                print(f'  {l}')
            return

        first_dates = first_activity_dates(issues)
        labeled = [i for i in issues if label in i.labels]
        first_timers = [i for i in labeled if is_first_time_reporter(i, first_dates)]

        print_intro('FirstReporterAnalysis',
                    question=f'Within `{label}`, are issues from first-time reporters resolved '
                             f'differently depending on how much of their description is '
                             f'pasted code?',
                    method=f'A first-time reporter had no earlier activity (issue created, or a '
                           f'{", ".join(ACTIVITY_EVENTS)} event) before opening the issue. Code '
                           f'share is measured on the `### {SECTION}` section only; issues '
                           f'without that section (old checkbox template) are left out. Issues '
                           f'are grouped into no code (share 0), top 10% (at or above the '
                           f'{TOP_PERCENTILE}th percentile of non-zero shares, ties included) '
                           f'and middle (the rest), then compared on median time to close '
                           f'(closed issues only, last close event), median comments, duplicate '
                           f'and needs-reproduction rates (current labels), and who closed them.')

        print(f'Found {len(first_timers)} issues from first-time reporters '
              f'out of {len(labeled)} issues labeled `{label}`.')

        sections = {i.number: extract_section(i, SECTION) for i in first_timers}
        with_section = [i for i in first_timers if sections[i.number] is not None]
        shares = {i.number: code_share(sections[i.number]) for i in with_section}
        print(f'Left out {len(first_timers) - len(with_section)} issues without a '
              f'`### {SECTION}` section.')
        cutoff = top_cutoff(list(shares.values()))
        if cutoff is not None:
            print(f'Top group cutoff: code share >= {cutoff:.3f}')
        print()

        groups:Dict[str, List[Issue]] = {g: [] for g in GROUPS}
        for issue in with_section:
            groups[share_group(shares[issue.number], cutoff)].append(issue)

        maintainers = find_maintainers(issues)
        stats = {g: self._group_stats(members, maintainers) for g, members in groups.items()}
        print_table(['group', 'n', 'n closed', 'median days to close', 'median comments',
                     'duplicate rate', 'needs-reproduction rate',
                     'closed by reporter', 'closed by maintainer', 'closed by other'],
                    [[g, f"n={s['n']}", s['closed'], fmt(s['median_days'], '.1f'),
                      fmt(s['median_comments'], 'g'), fmt(s['duplicate'], '.1%'),
                      fmt(s['needs_repro'], '.1%')]
                     + [self._closer_cell(s, c) for c in CLOSERS]
                     for g, s in stats.items()])

        small = [f"{g} (n={s['n']})" for g, s in stats.items() if s['n'] < MIN_GROUP_SIZE]
        if small:
            print(f'Warning: fewer than {MIN_GROUP_SIZE} issues in {", ".join(small)}; '
                  f'treat those numbers as anecdotal.\n')

        print_finding(self._finding(stats))

        if not any(s['n'] for s in stats.values()):
            print(f'No issues to group in `{label}`, so there is no chart.')
            return
        self.plot_groups(label, stats)

    def _group_stats(self, issues:List[Issue], maintainers) -> dict:
        """
        Returns n, the number closed, the median days to close, the median
        comment count, the duplicate and needs-reproduction rates, and the
        number of closed issues per closer type for a group's issues.
        """
        closers = [closer_type(i, maintainers) for i in issues]
        return {
            'n': len(issues),
            'closed': sum(1 for c in closers if c is not None),
            'median_days': median_days(time_to_close(i) for i in issues),
            'median_comments': statistics.median(comment_count(i) for i in issues)
                               if issues else None,
            'duplicate': rate(is_duplicate(i) for i in issues),
            'needs_repro': rate(needs_reproduction(i) for i in issues),
            'closers': {c: closers.count(c) for c in CLOSERS},
        }

    def _closer_cell(self, stats:dict, closer:str) -> str:
        """
        Returns the count of a group's closed issues closed by `closer`,
        with its share of the closed issues.
        """
        count = stats['closers'][closer]
        if not stats['closed']:
            return '-'
        return f"{count} ({count / stats['closed']:.0%})"

    def _finding(self, stats:dict) -> str:
        """
        Returns the finding text, comparing the top 10% group with the
        no-code group.
        """
        none, top = stats['no code'], stats['top 10%']
        if not none['n'] or not top['n']:
            return (f"Can't compare: the no-code group has n={none['n']} and the top 10% "
                    f"group has n={top['n']}.")

        def compare(t, n, spec, unit=''):
            if t is None or n is None:
                return 'could not be compared'
            word = 'higher' if t > n else 'lower' if t < n else 'the same'
            return f'{word} ({t:{spec}}{unit} vs {n:{spec}}{unit})'

        def reporter_share(s):
            return s['closers']['reporter'] / s['closed'] if s['closed'] else None

        text = (f"Compared with issues that have no code in their description, the top 10% "
                f"code-heavy issues have a median time to close that is "
                f"{compare(top['median_days'], none['median_days'], '.1f', ' days')}, a "
                f"median comment count that is "
                f"{compare(top['median_comments'], none['median_comments'], 'g')}, a "
                f"duplicate rate that is {compare(top['duplicate'], none['duplicate'], '.1%')}, "
                f"and a share closed by the reporter that is "
                f"{compare(reporter_share(top), reporter_share(none), '.0%')}.")
        if min(none['n'], top['n']) < MIN_GROUP_SIZE:
            text += ' One of the groups is too small for this to be more than anecdotal.'
        return text

    def plot_groups(self, label:str, stats:dict):
        """
        Plots median days to close per group next to a grouped bar chart of
        who closed each group's closed issues, as a share of those issues.
        """
        fig, (ax_days, ax_close) = plt.subplots(1, 2, figsize=(14, 6))
        names = [f"{g}\n(n={s['n']})" for g, s in stats.items()]
        x = np.arange(len(names))

        days = [s['median_days'] for s in stats.values()]
        ax_days.bar(x, [d if d is not None else 0 for d in days], color='tab:blue')
        # A group with no closed issues has no median; label it instead of showing a 0 bar
        for k, d in enumerate(days):
            if d is None:
                ax_days.annotate('no closed issues', (x[k], 0), xytext=(0, 4),
                                 textcoords='offset points', ha='center', fontsize=8)
        ax_days.set_xticks(x, names)
        ax_days.set_title('Median time to close')
        ax_days.set_xlabel('Description code share group')
        ax_days.set_ylabel('Median days to close (closed issues only)')
        ax_days.set_ylim(bottom=0)

        width = 0.8 / len(CLOSERS)
        for k, closer in enumerate(CLOSERS):
            shares = [s['closers'][closer] / s['closed'] if s['closed'] else 0
                      for s in stats.values()]
            ax_close.bar(x + (k - (len(CLOSERS) - 1) / 2) * width, shares, width,
                         label=closer)
        ax_close.set_xticks(x, names)
        ax_close.set_title('Who closed the issue')
        ax_close.set_xlabel('Description code share group')
        ax_close.set_ylabel('Share of closed issues')
        ax_close.set_ylim(0, 1)
        ax_close.legend(title='Closed by')

        fig.suptitle(f'First-time reporter issues labeled `{label}`, by code share of the description')
        fig.tight_layout()
        save_chart(fig, CHART_PATH)


if __name__ == '__main__':
    # Invoke run method when running this module directly
    FirstReporterAnalysis().run()
