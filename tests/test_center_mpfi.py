from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from minoverlap.baseline import compile_mpfi_verifier
from minoverlap.center_mpfi import parse_center_mpfi_output, run_center_mpfi

ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "verification" / "center_mpfi.c"
CERTIFICATE = ROOT / "certificates" / "center-038055925.tsv"


@pytest.fixture(scope="module")
def center_mpfi_binary(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return compile_mpfi_verifier(
        SOURCE,
        tmp_path_factory.mktemp("center-mpfi") / "center_mpfi",
    )


def valid_output() -> str:
    return "\n".join(
        [
            "backend=mpfi-c",
            "mpfi_version=1.5.4",
            "certificate_schema=minimum-overlap-center-certificate-v1",
            "precision_bits=256",
            "initial_cells=4096",
            "max_depth=16",
            "target=0.38055925",
            "cosine_rows=107",
            "parseval_order=100",
            "visited_cells=4",
            "negative_cells=1",
            "positive_cells=1",
            "split_cells=1",
            "terminal_cells=1",
            "max_depth_seen=16",
            "positive_antiderivative_upper=2.6",
            "uncertain_rectangle_upper=0.0001",
            "denominator_upper=2.6001",
            "target_denominator_exact=4000000/1522237",
            "target_denominator_lower=2.6277",
            "denominator_margin_lower=0.0276",
            "certified=true",
        ]
    )


def test_output_parser_accepts_strict_success() -> None:
    fields = parse_center_mpfi_output(valid_output())

    assert fields["certified"] == "true"
    assert fields["backend"] == "mpfi-c"


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        (lambda text: text + "\ncertified=true", "duplicate"),
        (lambda text: text.replace("certified=true", "certified=false"), "did not certify"),
        (
            lambda text: text.replace(
                "denominator_margin_lower=0.0276",
                "denominator_margin_lower=nan",
            ),
            "non-finite",
        ),
        (
            lambda text: text.replace(
                "target_denominator_lower=2.6277",
                "target_denominator_lower=2.5",
            ),
            "not strict",
        ),
    ],
)
def test_output_parser_rejects_untrusted_success_fields(
    mutation: object,
    match: str,
) -> None:
    assert callable(mutation)
    with pytest.raises(ValueError, match=match):
        parse_center_mpfi_output(mutation(valid_output()))


def test_released_center_certificate_passes_mpfi_verification(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    center_mpfi_binary: Path,
) -> None:
    monkeypatch.setattr(
        "minoverlap.center_mpfi.compile_mpfi_verifier",
        lambda _source, _output: center_mpfi_binary,
    )
    result = run_center_mpfi(
        SOURCE,
        CERTIFICATE,
        tmp_path / "center_mpfi",
        precision_bits=256,
        initial_cells=4_096,
        max_depth=16,
    )

    assert result["status"] == "pass"
    assert result["certificate_sha256"] == (
        "b02a45a645337c74215a365e82f403990eeb9413e3f8771e719e5e5397da39e8"
    )
    fields = result["fields"]
    assert isinstance(fields, dict)
    assert fields["certified"] == "true"


def test_launcher_binds_hash_to_bytes_consumed_by_c(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    certificate = tmp_path / "center.tsv"
    original = CERTIFICATE.read_bytes()
    certificate.write_bytes(original)

    class Completed:
        returncode = 0
        stdout = valid_output()
        stderr = ""

    def fake_run(command: list[str], **_: object) -> Completed:
        certificate.write_bytes(
            original.replace(b"target\t0.38055925", b"target\t0.3805593")
        )
        assert Path(command[1]).read_bytes() == original
        return Completed()

    monkeypatch.setattr(
        "minoverlap.center_mpfi.compile_mpfi_verifier",
        lambda _source, output: output,
    )
    monkeypatch.setattr("minoverlap.center_mpfi.subprocess.run", fake_run)

    result = run_center_mpfi(
        SOURCE,
        certificate,
        tmp_path / "center_mpfi",
    )

    assert result["certificate_sha256"] == (
        "b02a45a645337c74215a365e82f403990eeb9413e3f8771e719e5e5397da39e8"
    )


def run_direct(binary: Path, certificate: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(binary), str(certificate), "128", "16", "2"],
        check=False,
        text=True,
        capture_output=True,
    )


def simple_certificate(target: str = "0.2") -> str:
    return "\n".join(
        [
            "minimum-overlap-center-certificate-v1",
            f"target\t{target}",
            "mean_abs_max\t0.003125",
            "second_moment_multiplier\t0.000001",
            "parseval_order\t1",
            "parseval_multiplier\t0.000001",
            "cosine_count\t1",
            "cosine\t1\t0.000001",
            "",
        ]
    )


@pytest.mark.parametrize(
    "payload",
    [
        simple_certificate().replace("\n", "\r\n"),
        simple_certificate().replace("cosine_count\t1", "cosine_count\t2"),
        simple_certificate().replace("cosine\t1\t0.000001", "cosine\t1\t0"),
        simple_certificate() + "trailing\n",
        "\n".join(
            [
                "minimum-overlap-center-certificate-v1",
                "target\t0.2",
                "mean_abs_max\t0.003125",
                "second_moment_multiplier\t0.000001",
                "parseval_order\t1",
                "parseval_multiplier\t0.000001",
                "cosine_count\t2",
                "cosine\t2\t0.000001",
                "cosine\t1\t0.000001",
                "",
            ]
        ),
    ],
)
def test_c_parser_rejects_malformed_certificate(
    tmp_path: Path,
    center_mpfi_binary: Path,
    payload: str,
) -> None:
    certificate = tmp_path / "invalid.tsv"
    certificate.write_bytes(payload.encode("ascii"))

    completed = run_direct(center_mpfi_binary, certificate)

    assert completed.returncode == 2
    assert "status=parse_failure" in completed.stderr


def test_c_verifier_rejects_an_insufficient_target(
    tmp_path: Path,
    center_mpfi_binary: Path,
) -> None:
    certificate = tmp_path / "insufficient.tsv"
    certificate.write_text(simple_certificate("0.3"))

    completed = run_direct(center_mpfi_binary, certificate)

    assert completed.returncode == 1
    assert "certified=false" in completed.stdout
