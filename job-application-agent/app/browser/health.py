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
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return {
            "status": "unavailable",
            "package": "missing",
            "profile_path": str(profile_path),
            "error": str(exc),
        }

    with sync_playwright() as playwright:
        executable_path = Path(playwright.chromium.executable_path)

    if not executable_path.exists():
        return {
            "status": "unavailable",
            "package": "available",
            "profile_path": str(profile_path),
            "chromium_executable": str(executable_path),
            "error": "Chromium is not installed. Run `python -m playwright install chromium`.",
        }

    return {
        "status": "configured",
        "package": "available",
        "profile_path": str(profile_path),
        "chromium_executable": str(executable_path),
        "real_site_visits": "disabled_in_phase_1",
    }
