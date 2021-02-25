# github-tools

Collection of tools for studying/mining GitHub repos.

## list_repos.py

Lists the top n (in terms of stars) GitHub repos for a specific language
and the latest commit at its default branch.

## unpack_repo.py

Unpacks an entire repo .zip as a flat directory.
Optionally, it can record the original pathname of each flattened file
in a SQLite database.
