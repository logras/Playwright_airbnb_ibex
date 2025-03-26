from typing import Dict
import os

import allure
import pytest
import requests
from _pytest.fixtures import FixtureRequest, SubRequest
from _pytest.nodes import Item
from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import Page, Playwright, Error as PlaywrightError

from utilities.axe_helper import AxeHelper
from utilities.constants import Constants


@pytest.fixture(scope="function", autouse=True)
def goto(page: Page, request: SubRequest):
    """Fixture to navigate to the base URL based on the user.

    If the 'storage_state' is set in 'browser_context_args', it navigates to the inventory page,
    otherwise, it navigates to the login page.

    Args:
        page (Page): Playwright page object.
        request (SubRequest): Pytest request object to get the 'browser_context_args' fixture value.
            If 'browser_context_args' is set to a user parameter (e.g., 'standard_user'),
            the navigation is determined based on the user.

    Example:
        @pytest.mark.parametrize('browser_context_args', ["standard_user"], indirect=True)
    """
    if request.getfixturevalue("browser_context_args").get("booking_state"):
        page.goto("/rooms.html")
    else:
        page.goto("")


@pytest.fixture(scope="session")
def axe_playwright():
    """Fixture to provide an instance of AxeHelper with Axe initialized.

    This fixture has a session scope, meaning it will be created once per test session
    and shared across all tests.

    Returns:
        AxeHelper: An instance of AxeHelper with Axe initialized.
    """
    yield AxeHelper(Axe())


@pytest.fixture(scope="function")
def browser_context_args(
    browser_context_args: Dict, base_url: str, request: SubRequest
):
    """This fixture allows setting browser context arguments for Playwright.

    Args:
        browser_context_args (dict): Base browser context arguments.
        request (SubRequest): Pytest request object to get the 'browser_context_args' fixture value.
        base_url (str): The base URL for the application under test.
    Returns:
        dict: Updated browser context arguments.
    See Also:
        https://playwright.dev/python/docs/api/class-browser#browser-new-contex

    Returns:
        dict: Updated browser context arguments.
    """
    context_args = {
        **browser_context_args,
        "no_viewport": True,
        "user_agent": Constants.AUTOMATION_USER_AGENT,
    }

    if hasattr(request, "param"):
        context_args["storage_state"] = {
            "cookies": [
                {
                    "name": "session-username",
                    "value": request.param,
                    "url": base_url,
                }
            ]
        }
    return context_args


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args: Dict, playwright: Playwright):
    """Fixture to set browser launch arguments.

    This fixture updates the browser launch arguments to start the browser maximized
    and sets the test ID attribute for selectors.

    Args:
        browser_type_launch_args (Dict): Original browser type launch arguments.
        playwright (Playwright): The Playwright instance.

    Returns:
        Dict: Updated browser type launch arguments with maximized window setting.

    Note:
        This fixture has a session scope, meaning it will be executed once per test session.

    See Also:
        https://playwright.dev/python/docs/api/class-browsertype#browser-type-launch
    """
    playwright.selectors.set_test_id_attribute("data-test")
    return {**browser_type_launch_args, "args": ["--start-maximized"]}


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: Item, call):
    """Hook to mark test execution status in the request object.
    
    This hook marks the test execution status (passed, failed, etc.) in the request object,
    which can be used in fixtures to perform actions based on test status.
    
    Args:
        item: Pytest item object.
        call: Pytest call object.
    """
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


@pytest.fixture(autouse=True)
def attach_playwright_results(page: Page, request: FixtureRequest):
    """Fixture to perform teardown actions and attach results to Allure report
    on failure.

    Args:
        page (Page): Playwright page object.
        request: Pytest request object.
    """
    yield
    
    # Check if test has run and has failed
    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        try:
            allure.attach(
                body=page.url,
                name="URL",
                attachment_type=allure.attachment_type.URI_LIST,
            )
        except PlaywrightError as e:
            allure.attach(
                body=f"Could not get URL: {e}",
                name="URL Error",
                attachment_type=allure.attachment_type.TEXT,
            )
            
        try:
            screenshot = page.screenshot(full_page=True)
            allure.attach(
                screenshot,
                name="Screen shot on failure",
                attachment_type=allure.attachment_type.PNG,
            )
        except PlaywrightError as e:
            allure.attach(
                body=f"Could not take screenshot: {e}",
                name="Screenshot Error",
                attachment_type=allure.attachment_type.TEXT,
            )
            
        try:
            allure.attach(
                body=get_public_ip(),
                name="public ip address",
                attachment_type=allure.attachment_type.TEXT,
            )
        except Exception as e:
            allure.attach(
                body=f"Could not get public IP: {e}",
                name="IP Error",
                attachment_type=allure.attachment_type.TEXT,
            )

@pytest.fixture(scope="function")
def context(browser):
    """Configure Playwright context to save videos only for failed tests"""
    context = browser.new_context(record_video_dir="videos/")  # Save videos in the 'videos' folder
    yield context
    context.close()

@pytest.fixture(scope="function")
def page(context):
    """Create a new page instance"""
    page = context.new_page()
    yield page
    page.close()

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item):
    """Attach video to Allure report if the test fails"""
    outcome = yield
    report = outcome.get_result()

    # If the test failed, attach the video
    if report.failed:
        page = item.funcargs.get("page")
        if page and page.video:
            video_path = page.video.path()
            if video_path and os.path.exists(video_path):
                with open(video_path, "rb") as video_file:
                    allure.attach(video_file.read(), name="Test Failure Video", attachment_type=allure.attachment_type.WEBM)
