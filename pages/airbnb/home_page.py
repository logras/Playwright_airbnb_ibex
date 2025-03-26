import allure
import logging
from playwright.sync_api import Page, expect
from utilities.constants import Constants as CONST


from pages.airbnb.components.search_bar import SearchBar

# Configure logging
logger = logging.getLogger("AirbnbHomePage")

@allure.severity(allure.severity_level.NORMAL)
@allure.story("Airbnb homepage behavior")
class HomePage:
    """HomePage object for Airbnb using component-based architecture.
    
    This page object represents the Airbnb homepage and uses
    the SearchBar component.
    
    Attributes:
        page (Page): The Playwright page object.
        search_bar (SearchBar): The search bar component.
    """
    
    def __init__(self, page: Page, viewport_size=None):
        self.page = page
        
        # Define expected viewport size
        self.expected_viewport = viewport_size or {"width": 1920, "height": 1080}
        
        # Initialize the search bar component
        self.search_bar = SearchBar(page, self.expected_viewport)
        
        # Initialize page elements with data-testid selectors
        self.logo = page.locator("[data-testid='header-logo']")
        self.profile_menu = page.locator("[data-testid='header-profile']")
        self.language_selector = page.locator("button[aria-label*='language']").first
        
    @allure.step("Navigate to Airbnb homepage")
    def navigate(self) -> None:
        """Navigate to the Airbnb homepage."""
        try:
            # Enforce full screen before navigation
            self._ensure_full_screen()
            
            logger.info("Navigating to Airbnb homepage...")
            # Navigate with longer timeout
            self.page.goto(CONST.BASE_URL, timeout=60000)
            
            # Log the current URL
            current_url = self.page.url
            logger.info(f"Navigated to: {current_url}")
            
            # Wait for the page to load with timeouts and error handling
            try:
                logger.info("Waiting for network idle...")
                self.page.wait_for_load_state("networkidle", timeout=30000)
            except Exception as e:
                logger.warning(f"Network idle timeout: {e}")
                # Try to continue anyway
            
            try:
                logger.info("Waiting for DOM content loaded...")
                self.page.wait_for_load_state("domcontentloaded", timeout=15000)
            except Exception as e:
                logger.warning(f"DOM content loaded timeout: {e}")
                # Try to continue anyway
            
            # Wait for key elements to be visible
            logger.info("Checking for key elements on the page...")
            selectors_to_try = [
                self.logo,
                self.page.locator("header"),
                self.page.locator("[data-testid='little-search']"),
                self.page.locator("[role='banner']"),
                self.page.locator("div[role='main']"),
                self.page.locator("body > div")  # Any div directly under body
            ]
            
            element_found = False
            for selector in selectors_to_try:
                try:
                    if selector.is_visible(timeout=5000):
                        logger.info(f"Found visible element on page")
                        element_found = True
                        break
                except Exception as e:
                    continue
            
            if not element_found:
                logger.warning("No key elements found on page, but continuing...")
            
            # Check viewport size again after navigation
            self._ensure_full_screen()
            
            # Take a screenshot of the full viewport for debugging
            try:
                allure.attach(
                    self.page.screenshot(full_page=True),
                    name="Full Page Homepage",
                    attachment_type=allure.attachment_type.PNG
                )
                logger.info("Screenshot taken successfully")
            except Exception as e:
                logger.warning(f"Failed to take screenshot: {e}")

            
        except Exception as e:
            logger.error(f"Error navigating to Airbnb homepage: {e}")
            # Try to capture a screenshot of whatever state we're in
            try:
                allure.attach(
                    self.page.screenshot(),
                    name="Navigation Error",
                    attachment_type=allure.attachment_type.PNG
                )
            except Exception as screenshot_error:
                logger.error(f"Could not take screenshot after navigation error: {screenshot_error}")
            
            # Re-raise the error
            raise

    def _verify_on_homepage(self) -> bool:
        """Verify that we are on the Airbnb homepage.

        Returns:
            bool: True if we are on the homepage, False otherwise.
        """
        try:
            # Check URL
            current_url = self.page.url.lower()
            if "airbnb.com" not in current_url:
                logger.warning(f"URL doesn't contain airbnb.com: {current_url}")
                return False

            # Check for expected elements
            homepage_indicators = [
                (self.logo, "logo"),
                (self.page.locator("[data-testid='little-search']"), "search box"),
                (self.page.locator("header"), "header")
            ]

            for indicator, name in homepage_indicators:
                if indicator.is_visible(timeout=1000):
                    logger.info(f"Found homepage indicator: {name}")
                    return True

            logger.warning("No homepage indicators found")
            return False

        except Exception as e:
            logger.error(f"Error verifying homepage: {e}")
            return False
        
    @allure.step("Handle popups")
    def _handle_popups(self) -> None:
        """Handle any popups that might appear on the page."""
        # Try various cookie consent selectors
        cookie_test_ids = [
            "accept-btn",
            "accept-cookies",
            "cookie-policy-manage-button",
            "main-cookies-bar-agree"
        ]

        # First try with locator using data-testid
        for test_id in cookie_test_ids:
            try:
                cookie_button = self.page.locator(f"[data-testid='{test_id}']")
                if cookie_button.is_visible(timeout=1000):
                    cookie_button.click()
                    self.page.wait_for_timeout(1000)  # Wait for popup to disappear
                    break
            except:
                continue

        # Try with attribute selectors if test_ids don't work
        cookie_selectors = [
            "button[aria-label*='Accept']",
            "button[aria-label*='accept']",
            "button[aria-label*='Cookie']"
        ]

        for selector in cookie_selectors:
            try:
                cookie_button = self.page.locator(selector).first
                if cookie_button.is_visible(timeout=1000):
                    cookie_button.click()
                    self.page.wait_for_timeout(1000)  # Wait for popup to disappear
                    break
            except:
                continue

        # Handle any other popups that might appear
        close_test_ids = ["close", "modal-close-button"]

        # First try with locator for data-testid
        for test_id in close_test_ids:
            try:
                close_button = self.page.locator(f"[data-testid='{test_id}']")
                if close_button.is_visible(timeout=1000):
                    close_button.click()
                    self.page.wait_for_timeout(1000)  # Wait for popup to disappear
                    break
            except:
                continue

        # Try with attribute selectors
        close_selectors = [
            "button[aria-label='Close']",
            "button[aria-label='close']",
            "button.close"
        ]

        for selector in close_selectors:
            try:
                close_button = self.page.locator(selector).first
                if close_button.is_visible(timeout=1000):
                    close_button.click()
                    self.page.wait_for_timeout(1000)  # Wait for popup to disappear
                    break
            except:
                continue

    @allure.step("Click on profile menu")
    def click_profile_menu(self) -> None:
        """Click on the profile menu."""
        self.profile_menu.click()

    @allure.step("Click on language selector")
    def click_language_selector(self) -> None:
        """Click on the language selector."""
        self.language_selector.click()
        
    @allure.step("Click on logo")
    def click_logo(self) -> None:
        """Click on the Airbnb logo."""
        self.logo.click()
        
    def _ensure_full_screen(self) -> None:
        """Ensure the browser is in full screen mode (1920x1080)."""
        current_viewport = self.page.viewport_size

        if current_viewport != self.expected_viewport:
            logger.warning(f"[HomePage] Viewport changed! Resetting from {current_viewport} to {self.expected_viewport}")
            # Log the change
            allure.attach(
                f"Viewport changed on homepage! Resetting from {current_viewport} to {self.expected_viewport}",
                name="HomePage Viewport Reset",
                attachment_type=allure.attachment_type.TEXT
            )
            
            # Force browser to full screen
            self.page.set_viewport_size(self.expected_viewport)
            
            # Bring the window to front to ensure it keeps focus
            self.page.context.pages[0].bring_to_front()
            
            # Wait for the viewport size to take effect
            self.page.wait_for_timeout(500)
        else:
            logger.info(f"[HomePage] Viewport check OK: {current_viewport}") 