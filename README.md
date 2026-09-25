# pin-gecko-deps

Two scripts to keep a Rust workspace's `Cargo.lock` aligned with Firefox/Gecko's
lockfile. Originally written for [neqo](https://github.com/mozilla/neqo).

Both must be run from the target workspace's **root** (where its `Cargo.lock` lives),
not from a checkout of this repo. Dependencies are resolved automatically by `uv`.

## Compare versions

```shell
uvx --from git+https://github.com/larseggert/pin-gecko-deps compare-lockfile
```

Fetches Gecko's `Cargo.lock` and reports which packages match, which differ,
and whether mismatches are production-affecting or dev/build-only.

## Update versions

```shell
uvx --from git+https://github.com/larseggert/pin-gecko-deps update-lockfile
```

Aligns shared dependencies with Gecko's pinned versions and updates packages
Gecko doesn't depend on (dev/build tools and workspace-exclusive packages) to
their latest available versions.

Set `GITHUB_TOKEN` (or `GITHUB_API_TOKEN`) in the environment to avoid GitHub
API rate limits when fetching Gecko metadata.

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
