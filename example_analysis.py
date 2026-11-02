from typing import List
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from data_loader import DataLoader
from model import Issue,Event
import config

class ExampleAnalysis:
    """
    Implements an example analysis of GitHub
    issues and outputs the result of that analysis.
    """
    
    def __init__(self):
        """
        Constructor
        """
        # Parameter is passed in via command line (--user)
        self.USER:str = config.get_parameter('user')
    
    def run(self):
        """
        Starting point for this analysis.
        
        Note: this is just an example analysis. You should replace the code here
        with your own implementation and then implement two more such analyses.
        """
        issues:List[Issue] = DataLoader().get_issues()
        
        ### BASIC STATISTICS
        # Calculate the total number of events for a specific user (if specified in command line args)
        total_events:int = 0
        for issue in issues:
            total_events += len([e for e in issue.events if self.USER is None or e.author == self.USER])
        
        output:str = f'Found {total_events} events across {len(issues)} issues'
        if self.USER is not None:
            output += f' for {self.USER}.'
        else:
            output += '.'
        print('\n\n'+output+'\n\n')
        

        ### BAR CHART
        # Display a graph of the top 50 creators of issues
        top_n:int = 50
        # Create a dataframe (with only the creator's name) to make statistics a lot easier
        df = pd.DataFrame.from_records([{'creator':issue.creator} for issue in issues])
        # Determine the number of issues for each creator and generate a bar chart of the top N
        df_hist = df.groupby(df["creator"]).value_counts().nlargest(top_n).plot(kind="bar", figsize=(14,8), title=f"Top {top_n} issue creators")
        # Set axes labels
        df_hist.set_xlabel("Creator Names")
        df_hist.set_ylabel("# of issues created")
        # Plot the chart
        plt.show() 
                        
    

if __name__ == '__main__':
    # Invoke run method when running this module directly
    ExampleAnalysis().run()