import allure
import pytest
import logging
import os
from datetime import datetime, timedelta
from playwright.sync_api import Page, expect, Error as PlaywrightError

from pages.airbnb.home_page import HomePage
from pages.airbnb.search_results_page import SearchResultsPage
from utilities.constants import Constants as CONST


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AirbnbTest")

@allure.epic("Airbnb Tests")
@allure.feature("Search Functionality")
class TestAirbnbSearch:
    """Test class for Airbnb search functionality.
    
    This test demonstrates the use of locator with data-testid for more maintainable
    and readable selectors throughout the page objects and components.
    """
    
    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        """Setup for the test.
        
        Args:
            page: The Playwright page fixture.
        """
        self.page = page
        
        # Determine fullscreen viewport size either from environment variables or use default
        width = int(os.environ.get("VIEWPORT_WIDTH", "1920"))
        height = int(os.environ.get("VIEWPORT_HEIGHT", "1080"))
        self.expected_viewport = {"width": width, "height": height}
        
        self.home_page = HomePage(page, self.expected_viewport)
        self.results_page = SearchResultsPage(page, self.expected_viewport)
        self.search_results_page = SearchResultsPage(page, self.expected_viewport)



        # Set longer timeout for all actions
        page.set_default_timeout(30000)
        self.home_page.search_bar.set_default_lang()

        
        # Add a yield to make sure this runs after the test
        yield
        
        # Check final viewport size matches what we expect to catch any changes
        try:
            final_viewport = page.viewport_size
            if final_viewport != self.expected_viewport:
                logger.warning(f"[TEST TEARDOWN] Viewport changed during test! Expected: {self.expected_viewport}, Actual: {final_viewport}")
                allure.attach(
                    f"Viewport changed during test! Expected: {self.expected_viewport}, Actual: {final_viewport}",
                    name="Viewport Size Issue",
                    attachment_type=allure.attachment_type.TEXT
                )
            else:
                logger.info(f"[TEST TEARDOWN] Viewport remained consistent at {final_viewport}")
        except PlaywrightError as e:
            logger.warning(f"[TEST TEARDOWN] Error checking viewport: {e}")

            # Take a full-page screenshot of the failure, with safe error handling
            try:
                screenshot = self.page.screenshot(full_page=True)
                allure.attach(
                    screenshot,
                    name="Error Screenshot - Full Page",
                    attachment_type=allure.attachment_type.PNG
                )
            except PlaywrightError as pe:
                logger.warning(f"[ERROR] Could not take screenshot: {pe}")
                allure.attach(
                    f"Could not take screenshot: {pe}",
                    name="Screenshot Error",
                    attachment_type=allure.attachment_type.TEXT
                )

            # Attach error details
            allure.attach(
                f"{type(e).__name__}: {e}",
                name="Error Details",
                attachment_type=allure.attachment_type.TEXT
            )

    # Generate a timestamp for the allure title
    test_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    @pytest.mark.airbnb_sanity
    @allure.title(f"Search for a stay in Amsterdam - {test_timestamp}")
    @allure.description("This test navigates to the Airbnb homepage, searches for a stay in Amsterdam for 2 adults and 1 child, and verifies that search results are displayed.")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_search_for_stay(self, setup):
        """Test searching for a stay on Airbnb using data-testid selectors."""
        destination = "Amsterdam"
        check_in_days_from_now = 1
        check_out_days_from_now = 2
        adults_count = 2
        child_count = 1
        new_child_count = 0
        new_delta_days = 7
        
        # Log the actual test run timestamp for comparison with the title timestamp
        run_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"[TEST INFO] Test running at {run_timestamp}, title timestamp is {self.test_timestamp}")
        
        try:

            search_bar = self.home_page.search_bar
            search_results = self.results_page.search_results
            search_results_page =  self.search_results_page

            # Step 1: Set the destination
            search_bar.set_search_destination(destination=destination)

            # Step 2: Set the dates
            search_bar.set_trip_dates(
                check_in_days_from_now=check_in_days_from_now, 
                check_out_days_from_now=check_out_days_from_now
            )

            # Step 3: Set the passengers
            search_bar.set_passengers(adults=adults_count, children=child_count)

            # Step 4: Click search
            search_bar.click_search_button(destination, check_in_days_from_now, check_out_days_from_now)
            
            # Take full-page screenshot of the results
            allure.attach(
                self.page.screenshot(full_page=True),
                name="Search Results - Full Page",
                attachment_type=allure.attachment_type.PNG
            )
            
            # Step 5: Select the highest-rated listing and validate
            logger.info("Selecting the highest-rated listing from search results")
            popup_card_details = search_results.select_highest_rated_listing()

            search_results_page.validate_highest_rated_listing_details(popup_card_details, adults_count, child_count, check_in_days_from_now, check_out_days_from_now)

            # Step 6 - update listing details guests
            search_results_page.remove_kids_from__highest_rated_listing(popup_card_details, new_child_count)
            # search_results_page.update_highest_rated_listing_details(popup_card_details, new_child_count, check_in_days_from_now, check_out_days_from_now, new_delta_days)

            #Step 7 - update listing details dates
            search_results_page.update_highest_rated_listing_date(popup_card_details, check_in_days_from_now, check_out_days_from_now, new_delta_days=7)


        except Exception as e:
            logger.error(f"[TEST ERROR] {type(e).__name__}: {e}")

            # Re-raise the exception to fail the test
            raise 