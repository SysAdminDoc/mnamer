from pathlib import Path

DOCKERFILE = Path(__file__).parents[2] / "Dockerfile"


def test_dockerfile_is_multiarch_and_non_root():
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert "FROM python:3.12-slim" in dockerfile
    assert "ARG UID=1000" in dockerfile
    assert "ARG GID=1000" in dockerfile
    assert "USER mnamer" in dockerfile
    assert 'VOLUME ["/config", "/mnt"]' in dockerfile


def test_dockerfile_uses_config_workdir_and_media_mount():
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert "WORKDIR /config" in dockerfile
    assert 'CMD ["--batch", "/mnt"]' in dockerfile
    assert "--create-home --home-dir /home/mnamer" in dockerfile
