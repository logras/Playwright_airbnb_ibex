import os
import pytest
from typing import Dict, Generator
from playwright.sync_api import Browser, BrowserContext, Page, Playwright


@pytest.fixture(scope="function")
def browser_context_args(browser_context_args: Dict) -> Dict:
    """This fixture extends the browser context arguments for Airbnb tests.
    
    It sets additional options like viewport size, locale, and timezone.
    
    Args:
        browser_context_args (Dict): Base browser context arguments.
        
    Returns:
        Dict: Updated browser context arguments.
    """
    return {
        **browser_context_args,
        # Set a specific viewport size for better layout rendering
        "viewport": {"width": 1920, "height": 1080},
        # Set locale and timezone for consistent date formats
        "locale": "en-US",
        "timezone_id": "Europe/Amsterdam",
        # Record video of tests
        "record_video_dir": "test-results/videos/airbnb",
        # Accept all cookies/permissions to avoid popups
        "permissions": ["geolocation"]
    }


@pytest.fixture(scope="function")
def page(browser: Browser, browser_context_args: Dict) -> Generator[Page, None, None]:
    """This fixture creates a new browser context and page for each test.
    
    Args:
        browser (Browser): The browser instance.
        browser_context_args (Dict): Browser context arguments.
        
    Yields:
        Page: The page object.
    """
    # Create a new context for each test
    context = browser.new_context(**browser_context_args)
    
    # Create a new page in the context
    page = context.new_page()
    
    # Set default timeout for all operations
    page.set_default_timeout(30000)
    
    # Yield the page object to the test
    yield page
    
    # Close the context after the test
    context.close()


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args: Dict) -> Dict:
    """Fixture to set browser launch arguments.
    
    Args:
        browser_type_launch_args (Dict): Original browser type launch arguments.
        
    Returns:
        Dict: Updated browser type launch arguments.
    """
    return {
        **browser_type_launch_args,
        "slow_mo": 100,  # Add a small delay between actions for better stability
    } 