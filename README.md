# GitMover
A Python script to migrate GitHub issues between repositories. It supports copying between private and public repos, handles pagination of API responses for repos with many issues, and attempts to preserve labels.

## Dependencies
GitMover is just a Python script. You'll need `requests`, `argparse` and a few
other Python modules installed. Install them with `pip`:

```
pip install -r requirements.txt
```

## Usage
```bash
$ git-mover.py [-h] [--destinationToken [DESTINATIONTOKEN]]
                    [--destinationUserName [DESTINATIONUSERNAME]]
                    [--sourceRoot [SOURCEROOT]]
                    [--destinationRoot [DESTINATIONROOT]]
                    [--numbers NUMBERS]
                    [--allIssues]
                    user_name token source_repo destination_repo
```

For authentication, GitMover uses a personal access token, which can be generated in your GitHub Profile settings.

### Positional Arguments
  `user_name`: Your GitHub (public or enterprise) username: name@email.com

  `token`: Your GitHub (public or enterprise) personal access token. ([instructions to create a token](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token))

  `source_repo`: the team and repo to migrate from: `<team_name>/<repo_name>`

  `destination_repo`: the team and repo to migrate to: `<team_name>/<repo_name>`

### Optional Arguments
  `-h, --help`: show this help message and exit

  `--sourceRoot [SOURCEROOT], -sr [SOURCEROOT]`: The GitHub domain to migrate from. Defaults to https://www.github.com. For GitHub enterprise customers, enter the domain for your GitHub installation.

  `--destinationRoot [DESTINATIONROOT], -dr [DESTINATIONROOT]`: The GitHub domain to migrate to. Defaults to https://www.github.com. For GitHub enterprise customers, enter the domain for your GitHub installation.

  `--destinationToken [DESTINATIONTOKEN], -dt [DESTINATIONTOKEN]`: Your personal access token for the destination account, if you are migrating between different GitHub installations.

  `--destinationUserName [DESTINATIONUSERNAME], -dun [DESTINATIONUSERNAME]`: Username (email address) for destination account, if you are migrating between different GitHub installations.

  `--numbers NUMBERS, -n NUMBERS`:  Comma separated numbers of specific issues to migrate (or explicitly pass `--allIssues`)

  `--allIssues, -a`: Migrate all issues
