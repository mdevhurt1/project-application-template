import os
from datetime import datetime
from typing import List, Optional

import matplotlib.pyplot as plt
import pandas as pd

from data_loader import DataLoader
from issue_metrics import (close_date, code_share, form_sections_text, is_duplicate,
                           median_days, needs_reproduction, rate, time_to_close)
from model import Issue
from report import print_intro, print_table, print_finding

# The issue form puts this heading in every body it produces.
FORM_MARKER = '### Description'

# Share of issues created on or after a candidate date that must use the form
# for that date to count as the switch.
MIN_FORM_ADOPTION = 0.9

# Where the chart is saved, relative to the working directory (gitignored).
CHART_PATH = os.path.join('output', 'f1_code_share.png')

# Quarters with fewer issues than this are dropped from a line, since their
# medians are too noisy to read anything into.
MIN_ISSUES_PER_QUARTER = 20


def uses_form(issue:Issue) -> bool:
    """
    Returns whether the issue body was written with the new issue form.
    """
    return bool(issue.text) and FORM_MARKER in issue.text


def detect_switch_date(issues:List[Issue]) -> Optional[datetime]:
    """
    Returns the creation date of the earliest issue whose body contains
    FORM_MARKER and at least MIN_FORM_ADOPTION of the issues created on
    or after that date use it. Earlier matches that fail the check are
    outliers and are skipped. Returns None if no date passes. Issues
    without a creation date are ignored.
    """
    dated = sorted((i for i in issues if i.created_date is not None),
                   key=lambda i: (i.created_date, i.number))
    # Number of form issues from position k to the end
    form_from = [0] * (len(dated) + 1)
    for k in range(len(dated) - 1, -1, -1):
        form_from[k] = form_from[k + 1] + uses_form(dated[k])
    for k, issue in enumerate(dated):
        if uses_form(issue) and form_from[k] / (len(dated) - k) >= MIN_FORM_ADOPTION:
            return issue.created_date
    return None


class TemplateSwitchAnalysis:
    """
    Did Poetry's switch from a checkbox template to a GitHub issue form
    change what reports contain and how they're resolved?
    """

    def run(self):
        """
        Starting point for this analysis.
        """
        issues:List[Issue] = DataLoader().get_issues()
        switch_date = detect_switch_date(issues)
        if switch_date is None:
            print(f'No issue form switch found: no `{FORM_MARKER}` date is followed '
                  f'by at least {MIN_FORM_ADOPTION:.0%} form issues.')
            return

        dated = [i for i in issues if i.created_date is not None]
        before = [i for i in dated if i.created_date < switch_date]
        after_all = [i for i in dated if i.created_date >= switch_date]
        # Post-switch issues that bypassed the form (mostly maintainer tracking
        # issues) never saw it, so they're left out of the after period.
        after = [i for i in after_all if uses_form(i)]
        early_matches = [i for i in before if uses_form(i)]

        print_intro('TemplateSwitchAnalysis',
                    question='Did the switch from a checkbox template to a GitHub issue '
                             'form change how issues are resolved?',
                    method=f'The switch date is the creation date of the earliest issue whose '
                           f'body contains `{FORM_MARKER}` and after which at least '
                           f'{MIN_FORM_ADOPTION:.0%} of new issues use the form. Issues are split '
                           f'at that date and compared on median time to close (closed issues '
                           f'only, last close event), duplicate rate and needs-reproduction rate '
                           f'(current labels).')

        print(f'Switch date: {switch_date:%Y-%m-%d %H:%M} UTC')
        print(f'Form check: {len(after)} of {len(after_all)} issues created since then '
              f'({len(after) / len(after_all):.1%}) use the form; the other '
              f'{len(after_all) - len(after)} are left out of the after period.')
        if early_matches:
            print(f'Outliers before the switch (heading present but not followed by '
                  f'consistent form use; kept in the before period): '
                  f'{", ".join(f"#{i.number} ({i.created_date:%Y-%m-%d})" for i in early_matches)}')
        print()

        stats = {name: self._period_stats(group)
                 for name, group in [('before', before), ('after', after)]}
        print_table(['period', 'n', 'n closed', 'median days to close',
                     'duplicate rate', 'needs-reproduction rate'],
                    [[name, s['n'], s['closed'], self._fmt(s['median_days'], '.1f'),
                      self._fmt(s['duplicate'], '.1%'), self._fmt(s['needs_repro'], '.1%')]
                     for name, s in stats.items()])

        print_finding(self._finding(stats['before'], stats['after']))

        self.plot_quarterly_code_share(issues, switch_date)

    def _period_stats(self, issues:List[Issue]) -> dict:
        """
        Returns n, the number closed, the median days to close, and the
        duplicate and needs-reproduction rates for a period's issues.
        """
        return {
            'n': len(issues),
            'closed': sum(1 for i in issues if close_date(i) is not None),
            'median_days': median_days(time_to_close(i) for i in issues),
            'duplicate': rate(is_duplicate(i) for i in issues),
            'needs_repro': rate(needs_reproduction(i) for i in issues),
        }

    def _fmt(self, value:Optional[float], spec:str) -> str:
        return '-' if value is None else format(value, spec)

    def _finding(self, before:dict, after:dict) -> str:
        """
        Returns the finding text for the before/after table.
        """
        def change(b, a, spec):
            if b is None or a is None:
                return 'could not be compared'
            word = 'rose' if a > b else 'fell' if a < b else 'stayed'
            return f'{word} from {b:{spec}} to {a:{spec}}'

        return (f"After the switch, median time to close "
                f"{change(before['median_days'], after['median_days'], '.1f')} days, the "
                f"duplicate rate {change(before['duplicate'], after['duplicate'], '.1%')}, and "
                f"the needs-reproduction rate "
                f"{change(before['needs_repro'], after['needs_repro'], '.1%')}. The time-to-close "
                f"drop is mostly not the form's doing: post-switch issues have had months, not "
                f"years, to close, and only {before['closed']} of {before['n']} pre-switch issues "
                f"in the dataset are closed. Both label rates are low and rest on a handful of "
                f"issues per period.")

    def plot_quarterly_code_share(self, issues:List[Issue], switch_date:datetime):
        """
        Plots the median code share per creation quarter of the text reporters
        write themselves: the whole body before the switch, and only the
        form's free-text sections (Description, Workarounds) after it. The
        form wraps its other fields (configuration, logs, pyproject.toml) in
        code fences automatically, so the whole body after the switch is
        shown separately for context. The quarter containing the switch is
        split into a before and an after point.
        """
        records = []
        for issue in issues:
            if issue.created_date is None:
                continue
            after = issue.created_date >= switch_date
            form_text = form_sections_text(issue)
            if after and form_text is None:
                # Post-switch issue that didn't use the form
                continue
            records.append({
                # Drop the timezone so pandas can bucket by quarter without a warning
                'date': issue.created_date.replace(tzinfo=None),
                'after': after,
                'body_share': code_share(issue),
                'reporter_share': code_share(form_text if after else issue),
            })
        df = pd.DataFrame.from_records(records)
        df['quarter'] = df['date'].dt.to_period('Q')

        reporter = self._quarterly_stats(df, 'reporter_share')
        before = reporter[~reporter['after']]
        after = reporter[reporter['after']]
        body_after = self._quarterly_stats(df[df['after']], 'body_share')

        print(f'Quarterly code share (quarters with fewer than '
              f'{MIN_ISSUES_PER_QUARTER} issues are left out):')
        print_table(['quarter', 'period', 'n', 'reporter text median', 'whole body median'],
                    [[str(q), 'after' if after_switch else 'before', r['n'],
                      f"{r['median']:.2f}",
                      f"{body_after.loc[(q, after_switch), 'median']:.2f}"
                      if (q, after_switch) in body_after.index else '-']
                     for (q, after_switch), r in reporter.iterrows()])

        fig, ax = plt.subplots(figsize=(14, 8))
        color = 'tab:blue'
        for i, part in enumerate([before, after]):
            # Separate segments so the line breaks where the measured text changes
            ax.plot(part['x'], part['median'], marker='o', color=color,
                    label='Reporter-written text (median)' if i == 0 else None)
            ax.fill_between(part['x'], part['q1'], part['q3'], color=color, alpha=0.15,
                            label='Reporter-written text (middle 50%)' if i == 0 else None)
        ax.plot(body_after['x'], body_after['median'], marker='s', color='tab:grey',
                linestyle=':', label='Whole body after switch, incl. auto-fenced form fields (median)')
        ax.axvline(switch_date.replace(tzinfo=None), color='tab:red', linestyle='--',
                   label=f'Template switch ({switch_date:%Y-%m-%d})')
        ax.set_title('Median code share of issue text per quarter, before and after the issue-form switch')
        ax.set_xlabel('Quarter created')
        ax.set_ylabel('Code share (fraction of characters in fenced code blocks)')
        ax.set_ylim(0, 1)
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=2, fontsize=9)
        fig.text(0.5, 0.01,
                 'Reporter-written text is the whole body before the switch and the Description '
                 '+ Workarounds sections after it. Points sit at the median creation date of '
                 'their quarter; the switch quarter is split in two.',
                 ha='center', fontsize=9, wrap=True)
        fig.tight_layout(rect=(0, 0.04, 1, 1))
        os.makedirs(os.path.dirname(CHART_PATH), exist_ok=True)
        fig.savefig(CHART_PATH, dpi=150)
        print(f'Chart saved to {CHART_PATH}')
        # Agg can't open a window (no GUI toolkit or display), so only show when one can
        if plt.get_backend().lower() != 'agg':
            plt.show()

    def _quarterly_stats(self, df:pd.DataFrame, column:str) -> pd.DataFrame:
        """
        Returns the median and quartiles of `column` per (quarter, after)
        group, with `x` set to the group's median creation date. Keeps only
        groups with at least MIN_ISSUES_PER_QUARTER issues.
        """
        grouped = df.groupby(['quarter', 'after'])
        stats = pd.DataFrame({
            'x': grouped['date'].median(),
            'median': grouped[column].median(),
            'q1': grouped[column].quantile(0.25),
            'q3': grouped[column].quantile(0.75),
            'n': grouped[column].count(),
        })
        stats = stats[stats['n'] >= MIN_ISSUES_PER_QUARTER]
        stats['after'] = stats.index.get_level_values('after')
        return stats


if __name__ == '__main__':
    # Invoke run method when running this module directly
    TemplateSwitchAnalysis().run()
