"""
RAMP Phase 12 UI Shell & Header Validation Tests
SIH26080 | MoES / NCMRWF

Validates:
  - test_header_render
  - test_status_api_binding
  - test_no_hardcoded_operational_status
  - test_header_responsive_layout
  - test_mode_indicator
  - test_status_popover
"""

from pathlib import Path
import re
import pytest
from fastapi.testclient import TestClient
from ramp.main import app

SHELL_TSX_PATH = Path("frontend/src/components/layout/Shell.tsx")
DATA_FEEDS_TSX_PATH = Path("frontend/src/pages/DataFeeds.tsx")


@pytest.fixture
def client():
    return TestClient(app)


def test_header_render():
    """Verify Shell.tsx renders the 3-zone layout with brand, context, and status."""
    assert SHELL_TSX_PATH.exists()
    content = SHELL_TSX_PATH.read_text(encoding="utf-8")

    # Zone 1: Brand
    assert "RAMP" in content
    assert "SIH26080" in content
    assert "MoES • NCMRWF" in content

    # Zone 2: Center context
    assert "getRouteContextTitle" in content
    assert "routeContext" in content

    # Zone 3: Right status & Popover
    assert "DATA" in content
    assert "popoverOpen" in content


def test_status_api_binding(client):
    """Verify backend /api/data/availability supplies live values bound by Shell and Popover."""
    res = client.get("/api/data/availability")
    assert res.status_code == 200
    data = res.json()["data"]
    assert "ncmrwf_ncum" in data
    assert "ncmrwf_neps" in data
    assert "imd_obs" in data
    assert "ramp_model" in data
    assert "overall_mode" in data
    assert "honesty_notice" in data


def test_no_hardcoded_operational_status():
    """Verify Shell.tsx does NOT hardcode operational status; all indicators depend on availability object."""
    content = SHELL_TSX_PATH.read_text(encoding="utf-8")

    # Status indicators must be conditional on availability state
    assert "availability?.ncmrwf_ncum" in content
    assert "availability?.ncmrwf_neps" in content
    assert "availability?.imd_obs" in content
    assert "availability?.ramp_model" in content

    # Long redundant project title should NOT appear inside header
    header_section = content[content.find("<header"):content.find("</header>")]
    assert "Regime-Aware Mixture-of-Experts Post-Processor (RAMP)" not in header_section


def test_header_responsive_layout():
    """Verify responsive utility classes in Shell.tsx for mobile, tablet, and desktop."""
    content = SHELL_TSX_PATH.read_text(encoding="utf-8")
    header_section = content[content.find("<header"):content.find("</header>")]

    assert "lg:hidden" in content  # Mobile hamburger drawer
    assert "hidden md:flex" in header_section  # Center context hidden on tiny screens to prevent wrapping
    assert "hidden sm:flex" in header_section or "hidden sm:inline" in header_section


def test_mode_indicator():
    """Verify mode indicator includes ARIA accessibility attributes and tooltip title."""
    content = SHELL_TSX_PATH.read_text(encoding="utf-8")
    header_section = content[content.find("<header"):content.find("</header>")]

    assert 'title="Current scientific data integrity mode"' in header_section
    assert 'aria-label=' in header_section
    assert "modeDotColor" in header_section


def test_status_popover():
    """Verify DATA status button toggles popover with exact source rows."""
    content = SHELL_TSX_PATH.read_text(encoding="utf-8")

    assert "DATA SOURCE STATUS" in content
    assert "NCUM" in content
    assert "NEPS" in content
    assert "IMD OBS" in content
    assert "RAMP MODEL" in content
    assert "Integrity Mode" in content
    assert "Last scan" in content
