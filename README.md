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
  - `python-dotenv`

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

To create an environment variable, navigate to or create a .env file in the same directory as run.py (should be the root) and add "ENPM611_PROJECT_DATA_PATH:path/to/data/file.json". Then, add ".env" to the gitignore file (also in the root directory) so it won't be committed.

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
**Given an issue, which issues are related to it through references or discussion, and how do they compare?**

### Method

The analysis looks for references in each issue's title, body, and comments. It recognizes references written as `#1234`, `python-poetry/poetry#1234`, or `github.com/python-poetry/poetry/issues/1234`. It builds a map of outgoing references for every issue, then inverts that map to find incoming references. An issue is related to the target if either issue references the other. References to issue numbers not included in the dataset are omitted.

For each related issue, the report shows its state, how many texts reference the target, the earliest reference date, and its time to close. It also reports the time from the first reference to close; this can be negative when an issue is referenced after it has closed. The report includes the number of distinct commenters and how many are the issue reporter or a maintainer. The finding summarizes the target's close time and the related issues' close and reference-to-close times. The chart shows each issue's lifespan, creation date, first reference, and close date, with the target's lifespan highlighted.

The finding highlights the time to close of the target, how many related issues are closed, the median time to close for the related issues, and the median time from the first reference to the target to the close of the issue. We plot the issues with a bar for each related issue displaying the lifespan of the issue. We also plot the first reference, issue creation, and issue close. The date the target was closed is displayed as a vertical dashed line.

## Assumptions and limitations

The following assumptions are made:

- Only code inside fenced blocks counts in the calculation of code share.
- Issues that were closed multiple times use the last closed event date for their time to close calculation.
- Issues that have no closed event are skipped in time to close calculations.
- **Maintainers** are defined as anyone who added a label to or closed an issue they did not create.
- **First-time reporters** are defined as anyone without earlier issues created, `commented` events, `labeled` events, or `closed` events.
- Related issues counts reference both *from* and *to* the target issue.

The analyses were limited to testing on the Canvas provided datasets. Additional data may change or invalidate some of the findings. The analyses were built with the intention of being robust to extended datasets, but this edge case was not tested. The data the analyses were tested on ends 2024-10-20.

Analysis 1 has a small after-switch sample. This reduces the impact of the analysis as not many issues have been closed since the form switch in the data used in testing.

Analysis 2 can have small groups depending on the label selected. A note is printed if this is the case, but the impact of the analysis should be reassessed for such small groups. It also focuses on issues created after the form switch in order to utilize the `### Description` section which reduces its data pool. The analysis also suffers from our definition of maintainers. Since we consider anyone who closes an issue they did not create as a maintainer, it is impossible for the closed by other group to have anyone in it.

Analysis 3 drops references to PRs. This can affect the relation graph and result in the finding missing data.

## Contributions

### Marcus Hurt (@mdevhurt1)

Marcus created the repo and the GitHub project to track work. He made major contributions in issue creation and tracking. He was a core developer for the project code, merging management, and conflict resolution. He contributed several README sections. Marcus created the before and after component diagrams and contributed to the sequence diagram for milestone 1.

### Nithya Gnanasekar (@Nithya18)

Nithya contributed to project coordination by organizing team sync-ups and facilitating brainstorming sessions to define and refine the project's analyses. She created the Milestone 1 sequence diagram and actively reviewed GitHub issues and pull requests. She also contributed to feature development, implementation, and refinement, collaborating with the team to improve the overall project functionality.

### Jarred De Azevedo (@Jarred1102)

Jarred contributed to improving the project's configuration and setup process by implementing .env file support using python-dotenv. He updated run.py to automatically load environment variables, added the required dependencies, and updated the README with setup instructions. He also actively reviewed GitHub issue and approved pull requests.

## AI Use Disclosure

AI was used in the creation of this repository. Autofill suggestions, chats to further understand how the desired analyses could be approached, tools like [Claude Code](https://claude.com/claude-code) for debugging, development, and review. The authors of the code are responsible for its functionality. If a line of code was committed by a developer, it is expected they can explain that line and why it was written that way. While AI tools were essential to the concise, functional, and fast-paced development in this project, the authors have all contributed their ideas, opinions, and time to the orderly development of this project.
