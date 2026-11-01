
import json
import os
import sys
from typing import List

import config
from model import Issue

# Store issues as singleton to avoid reloads
_ISSUES:List[Issue] = None

class DataLoader:
    """
    Loads the issue data into a runtime object.
    """
    
    def __init__(self):
        """
        Constructor
        """
        self.data_path:str = config.get_parameter('ENPM611_PROJECT_DATA_PATH')
        
    def get_issues(self):
        """
        This should be invoked by other parts of the application to get access
        to the issues in the data file.
        """
        global _ISSUES # to access it within the function
        if _ISSUES is None:
            _ISSUES = self._load()
            print(f'Loaded {len(_ISSUES)} issues from {self.data_path}.')
        return _ISSUES
    
    def _load(self):
        """
        Loads the issues into memory. Exits with a message if the data
        file can't be found.
        """
        if not self.data_path or not os.path.isfile(self.data_path):
            sys.exit(f'Data file not found: {self.data_path}\n'
                     f'Set ENPM611_PROJECT_DATA_PATH to the path of poetry_issues_all.json '
                     f'(see README.md).')
        with open(self.data_path,'r') as fin:
            return [Issue(i) for i in json.load(fin)]
    

if __name__ == '__main__':
    # Run the loader for testing
    DataLoader().get_issues()