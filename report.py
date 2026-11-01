"""
Shared console output helpers so every analysis presents its
question, method and finding in the same format.
"""

import os
from typing import Any, List, Optional, Sequence

import matplotlib.pyplot as plt
import pandas as pd

RULE_WIDTH:int = 72


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
    Prints rows as aligned columns under the given headers, e.g. for
    before/after or group comparisons.
    """
    df = pd.DataFrame(rows, columns=list(headers))
    print(df.to_string(index=False))
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
    when a GUI backend is available.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=150)
    print(f'Chart saved to {path}')
    # Agg can't open a window (no GUI toolkit or display), so only show when one can
    if plt.get_backend().lower() != 'agg':
        plt.show()
