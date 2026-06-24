"""Tests for source_fingerprint (pure file-hashing logic, no bpy calls)."""
from app.geometry.cache.fingerprint import source_fingerprint


def _write(tmp_path, name, content):
    p = tmp_path / name
    p.write_bytes(content)
    return p


def test_fingerprint_is_12_hex_chars(tmp_path):
    a = _write(tmp_path, "a.py", b"print(1)")
    fp = source_fingerprint([a])
    assert len(fp) == 12
    assert all(c in "0123456789abcdef" for c in fp)


def test_fingerprint_is_deterministic(tmp_path):
    a = _write(tmp_path, "a.py", b"x = 1")
    assert source_fingerprint([a]) == source_fingerprint([a])


def test_fingerprint_changes_when_content_changes(tmp_path):
    a = _write(tmp_path, "a.py", b"x = 1")
    before = source_fingerprint([a])
    a.write_bytes(b"x = 2")
    assert source_fingerprint([a]) != before


def test_fingerprint_is_order_independent(tmp_path):
    a = _write(tmp_path, "a.py", b"x = 1")
    b = _write(tmp_path, "b.py", b"y = 2")
    assert source_fingerprint([a, b]) == source_fingerprint([b, a])


def test_fingerprint_dedupes_repeated_paths(tmp_path):
    a = _write(tmp_path, "a.py", b"x = 1")
    assert source_fingerprint([a, a]) == source_fingerprint([a])


def test_fingerprint_depends_on_format_version(tmp_path):
    a = _write(tmp_path, "a.py", b"x = 1")
    assert source_fingerprint([a], format_version=1) != source_fingerprint(
        [a], format_version=2
    )


def test_missing_file_is_handled_deterministically(tmp_path):
    missing = tmp_path / "nope.py"
    assert source_fingerprint([missing]) == source_fingerprint([missing])


def test_missing_differs_from_present(tmp_path):
    a = _write(tmp_path, "a.py", b"")  # present but empty
    missing = tmp_path / "a_missing.py"
    assert source_fingerprint([a]) != source_fingerprint([missing])


def test_filename_matters(tmp_path):
    # Same bytes, different names -> different fingerprint (names are folded in).
    a = _write(tmp_path, "a.py", b"same")
    b = _write(tmp_path, "b.py", b"same")
    assert source_fingerprint([a]) != source_fingerprint([b])


def test_empty_paths_still_produces_fingerprint():
    fp = source_fingerprint([])
    assert len(fp) == 12


def test_same_basename_in_different_dirs_is_deterministic(tmp_path):
    # Regression: cache/base.py and defects/base.py share a base name. Sorting
    # by base name alone left the order to set/hash-seed iteration, making the
    # fingerprint non-deterministic across processes. parent/name identity fixes
    # it. Determinism must hold regardless of input order.
    d1 = tmp_path / "cache"
    d2 = tmp_path / "defects"
    d1.mkdir()
    d2.mkdir()
    f1 = d1 / "base.py"
    f2 = d2 / "base.py"
    f1.write_bytes(b"AAA")
    f2.write_bytes(b"BBB")

    assert source_fingerprint([f1, f2]) == source_fingerprint([f2, f1])


def test_same_basename_content_assignment_matters(tmp_path):
    # Swapping which directory holds which content must change the fingerprint,
    # proving same-basename files are not collapsed together.
    d1 = tmp_path / "cache"
    d2 = tmp_path / "defects"
    d1.mkdir()
    d2.mkdir()
    (d1 / "base.py").write_bytes(b"AAA")
    (d2 / "base.py").write_bytes(b"BBB")
    before = source_fingerprint([d1 / "base.py", d2 / "base.py"])

    (d1 / "base.py").write_bytes(b"BBB")
    (d2 / "base.py").write_bytes(b"AAA")
    after = source_fingerprint([d1 / "base.py", d2 / "base.py"])

    assert before != after
