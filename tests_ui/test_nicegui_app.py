"""Headless UI test for the NiceGUI dashboard: every view opens and shows its key content."""
from nicegui.testing import User

CHECKS = {"Exposure": "Task detail", "Scenarios (O3)": "Impact scenarios to 2030", "Risk (O4)": "AI risk taxonomy",
          "Use-case assessor": "Indicative AI Act class", "Validation (O5)": "Validation results", "Overview": "Sub-sectors"}


async def test_all_views_render(user: User) -> None:
    await user.open("/")
    await user.should_see("Employment covered")
    for view, text in CHECKS.items():
        user.find(view).click()
        await user.should_see(text)
