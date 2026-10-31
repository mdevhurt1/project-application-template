

"""
Starting point of the application. This module is invoked from
the command line to run the analyses.
"""

import argparse

import config
from example_analysis import ExampleAnalysis
from template_switch_analysis import TemplateSwitchAnalysis
from first_reporter_code_share_analysis import FirstReporterAnalysis
from related_issues_analysis import RelatedIssuesAnalysis


def parse_args():
    """
    Parses the command line arguments that were provided along
    with the python command. The --feature flag must be provided as
    that determines what analysis to run. Optionally, you can pass in
    a user, a label and/or an issue to run analysis focusing on specific issues.
    
    You can also add more command line arguments following the pattern
    below.
    """
    ap = argparse.ArgumentParser("run.py")
    
    # Required parameter specifying what analysis to run
    ap.add_argument('--feature', '-f', type=int, required=True,
                    help='Which of the three features to run')
    
    # Optional parameter for analyses focusing on a specific user (i.e., contributor)
    ap.add_argument('--user', '-u', type=str, required=False,
                    help='Optional parameter for analyses focusing on a specific user')
    
    # Optional parameter for analyses focusing on a specific label
    ap.add_argument('--label', '-l', type=str, required=False,
                    help='Optional parameter for analyses focusing on a specific label')
    
    # Optional parameter for analyses focusing on a specific issue
    ap.add_argument('--issue', '-i', type=int, required=False,
                    help='Optional parameter for analyses focusing on a specific issue')
    
    return ap.parse_args()



# Parse feature to call from command line arguments
args = parse_args()
# Add arguments to config so that they can be accessed in other parts of the application
config.overwrite_from_args(args)
    
# Run the feature specified in the --feature flag
if args.feature == 0:
    ExampleAnalysis().run()
elif args.feature == 1:
    TemplateSwitchAnalysis().run()
elif args.feature == 2:
    FirstReporterAnalysis().run()
elif args.feature == 3:
    RelatedIssuesAnalysis().run()
else:
    print('Need to specify which feature to run with --feature flag.')
