# mergebot

Periodically poll a Github pull request and merge it automatically if all
checks pass.

## Requirements

* `python3`

## Usage

1. Create a personal access token at `https://github.com/settings/tokens`.
2. `export GITHUB_ACCESS_TOKEN='...'`
    * Tip: Save the `export` command in your `.bashrc`.
    * Or save it in a file named `env` and before running `mergebot.py`
      remember to `source ./env`.
1. `python3 mergebot.py <URL of your Pull Request>`.
    * Example: `python3 mergebot.py https://github.com/owner/repo/pull/1234`

The script will poll the PR status every 5 minutes. It will notify you if the
PR is not mergeable or if some checks have failed. If the PR is mergeable, it
will merge it and quit.
