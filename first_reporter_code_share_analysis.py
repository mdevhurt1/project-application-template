from datetime import datetime
from typing import Dict, List

from data_loader import DataLoader
from model import Issue
import config

# Label used when --label isn't given.
DEFAULT_LABEL = 'kind/bug'

# Event types that count as a user's own activity. Creating an issue
# also counts. Passive events like `subscribed` and `mentioned` don't.
ACTIVITY_EVENTS = ('commented', 'labeled', 'closed')


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
        print(f'Found {len(first_timers)} issues from first-time reporters '
              f'out of {len(labeled)} issues labeled `{label}`.')


if __name__ == '__main__':
    # Invoke run method when running this module directly
    FirstReporterAnalysis().run()
