"""
Shared console output helpers so every analysis presents its
question, method and finding in the same format.
"""

from typing import Any, List, Sequence

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
