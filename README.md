# pin-gecko-deps

Two scripts to keep a Rust workspace's `Cargo.lock` aligned with Firefox/Gecko's
lockfile. Originally written for [neqo](https://github.com/mozilla/neqo).

Both must be run from the target workspace's **root** (where its `Cargo.lock` lives),
not from a checkout of this repo. Dependencies are resolved automatically by `uv`.

## Compare versions

```shell
uvx --from git+https://github.com/larseggert/pin-gecko-deps compare-lockfile
```

Fetches Gecko's `Cargo.lock` and checks that ours is aligned with it. Hard
violations are duplicate versions Gecko doesn't itself carry, and shared
dependencies that can reach a Gecko build sitting on a version other than
Gecko's. Everything else is advisory: deps ahead of Gecko that the next vendor
picks up, drift Gecko's build can't see, and pins another crate's version
requirement rules out. Mismatches are labelled production-affecting or
dev/build-only.

Exit status is `0` when every invariant holds, `1` when there are hard
violations, and `2` if the check could not run (no `Cargo.lock`, `cargo` or
network failure) — so a broken environment is distinguishable from a real
violation.

## Update versions

```shell
uvx --from git+https://github.com/larseggert/pin-gecko-deps update-lockfile
```

Pins every dependency Gecko carries to Gecko's exact version, dev- and
build-dependencies included, staying as close to Gecko as cargo allows. That
includes moving to another semver line when every requirement allows Gecko's
version. Where a requirement rules Gecko's version out, the version is left alone
rather than bumped to latest. Packages Gecko has no version of, and packages only neqo uses
within Gecko, are bumped to their newest compatible version.

Drift is only a hard violation for packages whose version can reach a Gecko build
of neqo — those reachable via normal or build edges from the crates Gecko vendors.
For the rest, matching Gecko is preferred but harmless to miss.

Both commands end with the same markdown block, `Why each version differs from
Gecko`, explaining per package why its version is what it is and why that is
safe. `update-lockfile` prefixes it with `Lockfile changes`, a before → after
list of what that run moved. Both are paste-ready for a commit message or PR
description. `Cargo.lock` itself cannot carry the rationale: cargo reserializes
the file on every write and drops any hand-added comments.

Both need a working `cargo` (they read the resolved dependency graph via `cargo
metadata --locked`). Setting `GITHUB_TOKEN` (or `GITHUB_API_TOKEN`) is optional
and only raises GitHub's rate limit for the one API call that lists Gecko's
`netwerk/` crates.

## Installation

For one-off use, `uvx` (shown above) fetches and runs a command without
installing anything. To install both commands persistently:

```shell
uv tool install --from git+https://github.com/larseggert/pin-gecko-deps pin-gecko-deps
```

Or with `pip install .` / `pipx install .` from a checkout of this repo.

## Development

```shell
uv sync --group dev   # ruff, ty, pytest

uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pytest
```

## License

Licensed under the Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE)
or <http://www.apache.org/licenses/LICENSE-2.0>) or the MIT license
([LICENSE-MIT](LICENSE-MIT) or <http://opensource.org/licenses/MIT>), at your
option.
