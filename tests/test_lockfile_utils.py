# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# http://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or http://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
from pin_gecko_deps.lockfile_utils import (
    BlockedPin,
    PinPlan,
    align_package_with_gecko,
    by_nearness,
    classify_version_relation,
    collect_pin_targets,
    find_compatible_gecko_range,
    find_non_gecko_duplicates,
    find_pinnable_packages,
    get_duplicate_packages,
    group_by_semver_range,
    is_registry_package,
    pair_version_moves,
    parse_packages,
    run_cargo,
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
    assert get_duplicate_packages(lock) == {"foo": {"1.0.0", "1.1.0"}}


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
    gecko_versions = {"foo": {"1.0.0"}}
    assert find_non_gecko_duplicates(our_lock, gecko_versions) == {"foo": ["2.0.0"]}


def test_by_nearness_orders_higher_ascending_then_lower_descending():
    releases = ["0.70.0", "0.71.0", "0.73.1", "0.74.0"]
    assert by_nearness("0.72.1", releases) == [
        "0.73.1",
        "0.74.0",
        "0.71.0",
        "0.70.0",
    ]


def test_find_compatible_gecko_range_picks_closest_higher_range():
    by_range = {"1.0": ["1.0.0"], "1.2": ["1.2.0"], "1.5": ["1.5.0"]}
    assert find_compatible_gecko_range("1.1", by_range) == ["1.2.0"]
    assert find_compatible_gecko_range("1.6", by_range) == ["1.5.0"]
    assert find_compatible_gecko_range("0.1", {"0.2": ["0.2.0"]}) == []


def test_align_package_with_gecko_targets_other_semver_line():
    gecko = parse_packages(
        {
            "package": [
                _pkg("bindgen", "0.72.999", source=None),
                _pkg("bindgen", "0.73.1"),
            ]
        }
    )
    ours = parse_packages({"package": [_pkg("bindgen", "0.72.1")]})
    assert align_package_with_gecko("bindgen", gecko, ours) == {
        ("bindgen", "0.72.1"): ["0.73.1"]
    }


def test_collect_pin_targets_pins_across_lines_only_when_requirements_allow():
    gecko = parse_packages({"package": [_pkg("bindgen", "0.73.1")]})
    ours = parse_packages({"package": [_pkg("bindgen", "0.72.1")]})
    key = ("bindgen", "0.72.1")

    relaxed = {"bindgen": [("nss-rs", ">=0.72, <0.74")]}
    plan = collect_pin_targets({"bindgen"}, set(), gecko, ours, relaxed)
    assert plan.targets == {key: "0.73.1"}
    assert plan.blocked == {}

    strict = {"bindgen": [("nss-rs", "^0.72")]}
    plan = collect_pin_targets({"bindgen"}, set(), gecko, ours, strict)
    assert plan.targets == {}
    assert plan.blocked == {key: BlockedPin("0.73.1", "nss-rs", "^0.72")}


def test_collect_pin_targets_falls_back_to_a_gecko_version_requirements_allow():
    gecko = parse_packages({"package": [_pkg("foo", "1.2.3"), _pkg("foo", "1.2.5")]})
    ours = parse_packages({"package": [_pkg("foo", "1.2.0")]})
    reqs = {"foo": [("bar", "<=1.2.4")]}
    plan = collect_pin_targets({"foo"}, set(), gecko, ours, reqs)
    assert plan.targets == {("foo", "1.2.0"): "1.2.3"}
    assert plan.blocked == {}


def test_collect_pin_targets_skips_neqo_only_and_non_registry_packages():
    gecko = parse_packages({"package": [_pkg("foo", "1.2.5"), _pkg("bar", "1.2.5")]})
    ours = parse_packages(
        {
            "package": [
                _pkg("foo", "1.2.0"),
                _pkg("bar", "1.2.0", source="git+https://x"),
            ]
        }
    )
    plan = collect_pin_targets({"foo", "bar"}, {"foo"}, gecko, ours, {})
    assert plan == PinPlan({}, {})


def test_find_pinnable_packages_tracks_reachability_per_version():
    def node(pkg_id, *deps):
        return {
            "id": pkg_id,
            "deps": [{"pkg": d, "dep_kinds": [{"kind": k}]} for d, k in deps],
        }

    metadata = {
        "packages": [
            {"id": "v", "name": "neqo-common", "version": "0.1.0"},
            {"id": "s1", "name": "shlex", "version": "1.3.0"},
            {"id": "s2", "name": "shlex", "version": "2.0.1"},
            {"id": "t", "name": "tool", "version": "1.0.0"},
        ],
        "resolve": {
            "nodes": [
                node("v", ("s1", "build"), ("t", "dev")),
                node("t", ("s2", None)),
                node("s1"),
                node("s2"),
            ]
        },
    }
    gecko_lock = {
        "package": [
            _pkg("neqo-common", "0.1.0", source="git+https://github.com/mozilla/neqo")
        ]
    }
    assert find_pinnable_packages(metadata, gecko_lock) == {
        ("neqo-common", "0.1.0"),
        ("shlex", "1.3.0"),
    }


def test_pair_version_moves_pairs_same_line_then_in_order():
    assert pair_version_moves(["0.7.13"], ["0.7.14"]) == [("0.7.13", "0.7.14")]
    assert pair_version_moves(["0.72.1"], ["0.73.1"]) == [("0.72.1", "0.73.1")]
    assert pair_version_moves(["1.3.0"], []) == [("1.3.0", "")]
    assert pair_version_moves([], ["1.0.3"]) == [("", "1.0.3")]
    assert pair_version_moves(["0.12.1", "1.0.4"], ["1.0.3"]) == [
        ("0.12.1", ""),
        ("1.0.4", "1.0.3"),
    ]


def test_run_cargo_reports_missing_cargo_as_tool_error(monkeypatch):
    monkeypatch.setenv("PATH", "")
    try:
        run_cargo("--version")
    except SystemExit as e:
        assert e.code == 2
    else:
        raise AssertionError("expected SystemExit")
