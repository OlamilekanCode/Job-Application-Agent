from pathlib import Path

from app.config import Settings, get_settings


def ensure_browser_profile(settings: Settings | None = None) -> Path:
    resolved = settings or get_settings()
    resolved.playwright_profile_dir.mkdir(parents=True, exist_ok=True)
    return resolved.playwright_profile_dir


def playwright_health(settings: Settings | None = None) -> dict[str, object]:
    resolved = settings or get_settings()
    profile_path = ensure_browser_profile(resolved)
    try:
        import playwright  # noqa: F401

        package_status = "available"
    except Exception as exc:
        return {
            "status": "unavailable",
            "package": "missing",
            "profile_path": str(profile_path),
            "error": str(exc),
        }

    return {
        "status": "configured",
        "package": package_status,
        "profile_path": str(profile_path),
        "real_site_visits": "disabled_in_phase_1",
    }

