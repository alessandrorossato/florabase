import tomllib
from pathlib import Path


def test_backend_coverage_threshold_uses_exact_percentage() -> None:
    configuration = tomllib.loads(
        (Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    )

    pytest_options = configuration["tool"]["pytest"]["ini_options"]["addopts"].split()

    assert "--cov-fail-under=90" in pytest_options
    assert configuration["tool"]["coverage"]["report"]["precision"] >= 2
