# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# http://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or http://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
from pin_gecko_deps.lockfile_utils import (
    classify_version_relation,
    find_non_gecko_duplicates,
    get_duplicate_packages,
    group_by_semver_range,
    is_registry_package,
    parse_packages,
    semver_range,
    workspace_crates,
)

_REGISTRY_SOURCE = "registry+https://github.com/rust-lang/crates.io-index"


def _pkg(name, version, source=_REGISTRY_SOURCE, deps=None):
    pkg = {"name": name, "version": version}
    if source is not None:
        pkg["source"] = source
    if deps:
        pkg["dependencies"] = deps
    return pkg


def test_semver_range_extracts_major_minor():
    assert semver_range("1.2.3") == "1.2"
    assert semver_range("0.4.0") == "0.4"


def test_group_by_semver_range_buckets_versions():
    grouped = group_by_semver_range(["1.2.3", "1.2.4", "1.3.0"])
    assert grouped == {"1.2": ["1.2.3", "1.2.4"], "1.3": ["1.3.0"]}


def test_parse_packages_tracks_all_versions_of_a_package():
    lock = {"package": [_pkg("foo", "1.0.0"), _pkg("foo", "1.1.0")]}
    packages = parse_packages(lock)
    assert set(packages["foo"]) == {"1.0.0", "1.1.0"}


def test_get_duplicate_packages_only_returns_multi_version_packages():
    lock = {
        "package": [_pkg("foo", "1.0.0"), _pkg("foo", "1.1.0"), _pkg("bar", "2.0.0")]
    }
    assert get_duplicate_packages(lock) == {"foo": ["1.0.0", "1.1.0"]}


def test_workspace_crates_excludes_sourced_packages():
    lock = {
        "package": [_pkg("local-crate", "0.1.0", source=None), _pkg("foo", "1.0.0")]
    }
    assert workspace_crates(lock) == {"local-crate"}


def test_is_registry_package_distinguishes_local_patches():
    assert is_registry_package({"source": "registry+https://x"})
    assert not is_registry_package({"source": None})
    assert not is_registry_package({"source": "git+https://x"})


def test_classify_version_relation():
    assert classify_version_relation("1.2.3", []) == "no-range"
    assert classify_version_relation("1.2.3", ["1.2.3"]) == "match"
    assert classify_version_relation("1.2.3", ["1.2.4"]) == "behind"
    assert classify_version_relation("1.2.4", ["1.2.3"]) == "ahead"
    assert classify_version_relation("1.2.999", ["1.2.3"]) == "match"


def test_find_non_gecko_duplicates_flags_versions_outside_geckos_ranges():
    our_lock = {"package": [_pkg("foo", "1.0.0"), _pkg("foo", "2.0.0")]}
    gecko_versions = {"foo": [("1.0.0", "registry")]}
    assert find_non_gecko_duplicates(our_lock, gecko_versions) == {"foo": ["2.0.0"]}
