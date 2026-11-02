"""
Shared console output helpers so every analysis presents its
question, method and finding in the same format.
"""

import os
import re
import shutil
from typing import Any, List, Optional, Sequence

import matplotlib.pyplot as plt
import tabulate as tabulate_module
from tabulate import tabulate

RULE_WIDTH:int = 72
MIN_CHART_WIDTH:float = 12.0  # inches
TABLE_FALLBACK_WIDTH:int = 160  # columns, when the terminal size is unknown
# tabulate widens every column by 2 beyond its content, which would break the width fit below
tabulate_module.MIN_PADDING = 0
NUMBER = re.compile(r'^[-+]?[\d,]*\.?\d+%?$|^-$')


def print_intro(title:str, question:str, method:str):
    """
    Prints the analysis title followed by the question it answers
    and the method used to answer it.
    """
    print('\n' + '=' * RULE_WIDTH)
    print(title)
    print('=' * RULE_WIDTH)
    print(f'Question: {question}')
    print(f'Method:   {method}')
    print()


def print_table(headers:Sequence[str], rows:List[Sequence[Any]]):
    """
    Prints rows as a bordered grid under the given headers, e.g. for
    before/after or group comparisons. When the grid is wider than the
    terminal, the widest columns are narrowed and their text wraps onto
    extra lines inside the cell. Columns that hold only numbers are
    right-aligned.
    """
    headers = [str(h) for h in headers]
    cells = [[str(c) for c in row] for row in rows]
    columns = list(zip(headers, *cells))

    # A column can't be narrower than its longest unbreakable word
    floor = [max(len(w) for text in col for w in text.split() or ['']) for col in columns]
    widths = [max(len(text) for text in col) for col in columns]
    # Border characters take 3 per column plus 1 for the closing bar
    limit = shutil.get_terminal_size((TABLE_FALLBACK_WIDTH, 24)).columns
    while sum(widths) + 3 * len(widths) + 1 > limit:
        i = max(range(len(widths)), key=lambda k: widths[k] - floor[k])
        if widths[i] <= floor[i]:
            break  # nothing left to narrow, let the terminal wrap
        widths[i] -= 1

    # Cells are already strings, so keep tabulate from reparsing them as numbers
    align = ['right' if all(NUMBER.match(t) for t in col[1:]) else 'left' for col in columns]
    print(tabulate(cells, headers=headers, tablefmt='grid', disable_numparse=True,
                   colalign=align, maxcolwidths=widths, maxheadercolwidths=widths))
    print()


def print_finding(text:str):
    """
    Prints the finding of the analysis.
    """
    print(f'Finding: {text}')
    print('=' * RULE_WIDTH + '\n')


def fmt(value:Optional[float], spec:str) -> str:
    """
    Formats a value for a table cell, or '-' when it is None.
    """
    return '-' if value is None else format(value, spec)


def save_chart(fig, path:str):
    """
    Saves the figure to path, creating its folder if needed, and shows it
    when a GUI backend is available. Every chart gets the same light grid
    behind the data and a minimum width, so narrow figures stay readable.
    """
    width, height = fig.get_size_inches()
    if width < MIN_CHART_WIDTH:
        fig.set_size_inches(MIN_CHART_WIDTH, height)
    for ax in fig.axes:
        ax.set_axisbelow(True)
        ax.grid(True, which='major', color='lightgrey', linewidth=0.8, alpha=0.8)
        ax.grid(True, which='minor', axis='x', color='lightgrey', linewidth=0.4, alpha=0.5)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # 'tight' keeps legends placed outside the axes from being cut off
    fig.savefig(path, dpi=150, bbox_inches='tight')
    print(f'Chart saved to {path}')
    # Agg can't open a window (no GUI toolkit or display), so only show when one can
    if plt.get_backend().lower() != 'agg':
        plt.show()
