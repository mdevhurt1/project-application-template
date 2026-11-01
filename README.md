# Poetry Issue Analyses

A command-line application that analyzes the GitHub issues of the [Poetry](https://github.com/python-poetry/poetry/issues) open source project. It loads a JSON export of the issues and runs one of three analyses, each of which prints its findings to the terminal and saves a chart to `output/`:

1. **Template switch:** did moving from a checkbox issue template to a GitHub issue form change how issues are resolved?
2. **First-time reporters:** within one label, are issues from first-time reporters resolved differently depending on how much of their description is pasted code?
3. **Related issues:** which issues are linked to a given issue through references, and how do they compare?

## Requirements

- Python 3.12 (tested on 3.12.3)
- The dependencies in `requirements.txt`:
  - `python-dateutil`
  - `pandas`
  - `matplotlib`

## Setup

Clone the repository and navigate into it:

```
git clone git@github.com:mdevhurt1/project-application-template.git
cd project-application-template
```

Create and activate a virtual environment, then install the dependencies:

```
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Dataset

Download `poetry_issues_all.json` from the project assignment in Canvas. Then point the application at it by setting the `ENPM611_PROJECT_DATA_PATH` environment variable:

```
export ENPM611_PROJECT_DATA_PATH=/path/to/poetry_issues_all.json      # macOS / Linux
$env:ENPM611_PROJECT_DATA_PATH = "C:\path\to\poetry_issues_all.json"  # Windows PowerShell
```

or updating config.json `ENPM611_PROJECT_DATA_PATH` to point to the dataset path.

The environment variable takes precedence over the `ENPM611_PROJECT_DATA_PATH` entry in `config.json`. Use the variable rather than editing `config.json` to avoid committing your personal path. The dataset itself is gitignored and must not be committed.

## Running the analyses

Run every command from the repository root with the virtual environment active. Each feature is selected with `--feature` (`-f`):

| Feature | Command | Options |
| --- | --- | --- |
| 1. Template switch | `python run.py --feature 1` | None |
| 2. First-time reporters | `python run.py --feature 2 [--label <label>]` | `--label` (`-l`), default `kind/bug` |
| 3. Related issues | `python run.py --feature 3 --issue <number>` | `--issue` (`-i`), required, no default |

### Feature 1: template switch

```
python run.py --feature 1
```

Takes no options. The chart is saved to `output/f1_code_share.png`.

### Feature 2: first-time reporters

```
python run.py --feature 2
python run.py --feature 2 --label kind/feature
```

`--label` picks the issue label to analyze. Without it, the analysis uses `kind/bug` and says so. If the label isn't in the data, it prints the available labels and stops. The chart is saved to `output/f2_code_share_groups.png`.

### Feature 3: related issues

```
python run.py --feature 3 --issue 9191
```

`--issue` is the number of the issue to analyze. It has no default: without it, the command prints a usage message and stops. The chart is saved to `output/f3_related_issues.png`.

### Example analysis

`python run.py --feature 0` runs the example analysis that came with the course template. It prints basic information about the issues and accepts an optional `--user` (`-u`).
