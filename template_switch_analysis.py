from datetime import datetime, timezone
from typing import List

import matplotlib.pyplot as plt
import pandas as pd

from data_loader import DataLoader
from issue_metrics import code_share, form_sections_text
from model import Issue
from report import print_intro, print_table, print_finding

# Placeholder until #8's detect_switch_date() lands: the creation date of the
# first issue in the dataset that consistently uses the new issue form.
PLACEHOLDER_SWITCH_DATE = datetime(2024, 2, 26, tzinfo=timezone.utc)

# Quarters with fewer issues than this are dropped from a line, since their
# medians are too noisy to read anything into.
MIN_ISSUES_PER_QUARTER = 20


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
        switch_date = PLACEHOLDER_SWITCH_DATE

        # Pattern for presenting results; replace the placeholder values with real ones
        print_intro('TemplateSwitchAnalysis',
                    question='not implemented yet',
                    method='not implemented yet')
        print_table(['group', 'value'], [['before', '-'], ['after', '-']])
        print_finding('not implemented yet')

        self.plot_quarterly_code_share(issues, switch_date)

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
