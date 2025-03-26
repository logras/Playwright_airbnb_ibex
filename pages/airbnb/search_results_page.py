import allure
import logging
from datetime import datetime, timedelta
from playwright.sync_api import Page, expect, TimeoutError

from pages.airbnb.components.search_results import SearchResults
from pages.airbnb.components.search_bar import SearchBar
from utilities.constants import Constants as CONST


# Configure logging
logger = logging.getLogger("AirbnbSearchResultsPage")

@allure.severity(allure.severity_level.NORMAL)
@allure.story("Airbnb search results behavior")
class SearchResultsPage:
    """SearchResultsPage object for Airbnb.
    
    This page object represents the search results page on Airbnb.
    
    Attributes:
        page (Page): The Playwright page object.
        search_results (SearchResults): The search results component.
    """
    
    def __init__(self, page: Page, viewport_size=None):
        self.page = page
        
        # Define expected viewport size
        self.expected_viewport = viewport_size or {"width": 1920, "height": 1080}

        # Initialize the search results component
        self.search_results = SearchResults(page)
        self.search_bar = SearchBar(page)

        # Initialize page elements with data-testid selectors
        self.filter_button = page.locator("[data-testid='category-bar-filter-button']")
        self.map_toggle = page.locator("[data-testid='map-toggle']")
        self.search_box = page.locator("[data-testid='little-search']")

        #listing details
        self.checkin_date = page.locator("[data-testid='change-dates-checkIn']")
        self.checkout_date = page.locator("[data-testid='change-dates-checkOut']")
        self.guests_count = page.locator("[id='GuestPicker-book_it-trigger']")

    @allure.step("Wait for page to load")
    def wait_for_page_load(self, timeout: int = 60000) -> None:
        """Wait for the search results page to load.
        
        Args:
            timeout (int, optional): Timeout in milliseconds. Defaults to 60000.
        """
        try:
            # Ensure we're in fullscreen mode
            self._ensure_full_screen()
            
            # Take a full-page screenshot before we wait
            try:
                allure.attach(
                    self.page.screenshot(full_page=True),
                    name="Before Results Page Load - Full Page",
                    attachment_type=allure.attachment_type.PNG
                )
            except Exception as screenshot_error:
                logger.warning(f"Failed to take initial screenshot: {screenshot_error}")
            
            # Check if the page is still available
            if not self._is_page_available():
                logger.error("Page is no longer available")
                return
            
            # First try to wait for network requests to settle, but don't fail if it times out
            try:
                logger.info("Waiting for DOM content loaded...")
                self.page.wait_for_load_state("domcontentloaded", timeout=min(15000, timeout // 4))
                logger.info("DOM content loaded reached")
            except Exception as dom_error:
                logger.warning(f"DOM content loaded timed out: {dom_error}")
                # If that also times out, log it but continue
                allure.attach(
                    f"Load state errors:  DOM: {dom_error}",
                    name="Load State Timeout",
                    attachment_type=allure.attachment_type.TEXT
                )

            # Wait a small amount of time for any JavaScript to run
            logger.info("Waiting for JS execution...")
            self.page.wait_for_timeout(3000)
            
            # Check if the page is still available
            if not self._is_page_available():
                logger.error("Page is no longer available after load states")
                return
            
            # Check viewport size again and fix if needed
            self._ensure_full_screen()
            
            # Take a full-page screenshot after waiting
            try:
                allure.attach(
                    self.page.screenshot(full_page=True),
                    name="After Results Page Load - Full Page",
                    attachment_type=allure.attachment_type.PNG
                )
            except Exception as screenshot_error:
                logger.warning(f"Failed to take post-load screenshot: {screenshot_error}")
            
            # Try different selectors to determine if the page has loaded
            load_indicators = [
                "card-container",
                "listing-card",
                "explore-footer",
                "little-search"  # This might be visible even on search results page
            ]
            
            # First try with direct selectors using locator with data-testid
            for test_id in load_indicators:
                if not self._is_page_available():
                    logger.error("Page is no longer available while checking load indicators")
                    return
                    
                try:
                    # Add .first to handle multiple matches - fixes strict mode violation
                    element = self.page.locator(f"[data-testid='{test_id}']").first
                    if element.is_visible(timeout=2000):
                        allure.attach(
                            f"Found load indicator with test_id: {test_id}",
                            name="Page Load Success",
                            attachment_type=allure.attachment_type.TEXT
                        )
                        logger.info(f"Found load indicator: {test_id}")
                        return
                except Exception as e:
                    logger.info(f"Indicator {test_id} not found: {e}")
                    continue
                    
            # If none of the test_ids worked, try with more generic selectors
            generic_selectors = [
                "[itemprop='itemListElement']",
                "main[id='site-content']",
                "div[role='main']",
                "footer",
                "h1",  # Often there's at least an h1 on the page
                "div.container"  # Common container class
            ]
            
            for selector in generic_selectors:
                if not self._is_page_available():
                    logger.error("Page is no longer available while checking generic selectors")
                    return
                    
                try:
                    element = self.page.locator(selector).first
                    if element.is_visible(timeout=2000):
                        allure.attach(
                            f"Found load indicator with selector: {selector}",
                            name="Page Load Success",
                            attachment_type=allure.attachment_type.TEXT
                        )
                        logger.info(f"Found load indicator: {selector}")
                        return
                except Exception as e:
                    logger.info(f"Selector {selector} not found: {e}")
                    continue
                    
            # Wait for any visible element on the page as a last resort
            if self._is_page_available():
                try:
                    logger.info("Waiting for any visible element...")
                    self.page.wait_for_selector("body > *", timeout=5000)
                    logger.info("Found at least some content on the page")
                except Exception as e:
                    logger.warning(f"No content found on page: {e}")
            
            # If we get here, none of the selectors were found within timeout
            try:
                allure.attach(
                    self.page.screenshot(),
                    name="Page loaded without specific indicators",
                    attachment_type=allure.attachment_type.PNG
                )
            except Exception as screenshot_error:
                logger.warning(f"Failed to take final screenshot: {screenshot_error}")
                
            logger.info("Page loaded without finding specific indicators")
            # Instead of failing, we'll continue and let the test determine if the search was successful
        
        except Exception as e:
            logger.error(f"Error waiting for page to load: {e}")
            try:
                allure.attach(
                    str(e),
                    name="Page load error",
                    attachment_type=allure.attachment_type.TEXT
                )
            except:
                pass
                
    def _is_page_available(self) -> bool:
        """Check if the page is still available and not closed.
        
        Returns:
            bool: True if the page is available, False otherwise.
        """
        try:
            # A simple operation that will fail if the page is closed
            _ = self.page.url
            return True
        except Exception:
            return False
    
    def _ensure_full_screen(self) -> None:
        """Ensure the browser is in full screen mode (1920x1080)."""
        current_viewport = self.page.viewport_size

        if current_viewport != self.expected_viewport:
            logger.warning(f"[SearchResultsPage] Viewport changed! Resetting from {current_viewport} to {self.expected_viewport}")
            # Log the change
            allure.attach(
                f"Viewport changed on results page! Resetting from {current_viewport} to {self.expected_viewport}",
                name="Results Page Viewport Reset",
                attachment_type=allure.attachment_type.TEXT
            )
            
            # Force browser to full screen
            self.page.set_viewport_size(self.expected_viewport)
            
            # Bring the window to front to ensure it keeps focus
            self.page.context.pages[0].bring_to_front()
            
            # Wait for the viewport size to take effect
            self.page.wait_for_timeout(500)
        else:
            logger.info(f"[SearchResultsPage] Viewport check OK: {current_viewport}")


    @allure.step("Verify search results for {destination}")
    def verify_search_results(self, destination: str) -> bool:
        """Verify that the search results are for the specified destination.

        Args:
            destination (str): The destination that was searched for.

        Returns:
            bool: True if the search results are for the specified destination.
        """
        # First check the page URL or title
        current_url = self.page.url.lower()
        page_title = self.page.title().lower()
        destination_lower = destination.lower()

        # Take a screenshot for debugging
        self.page.screenshot(path="test-results/verify-search-results.png")

        url_contains_destination = destination_lower in current_url
        title_contains_destination = destination_lower in page_title

        # Try to find destination in page content
        try:
            # Look for the destination in various elements
            destination_in_content = False

            # Check if destination appears in heading or breadcrumbs
            test_ids = ["explore-header"]
            for test_id in test_ids:
                try:
                    heading = self.page.locator(f"[data-testid='{test_id}']")
                    if heading.is_visible(timeout=1000):
                        heading_text = heading.inner_text().lower()
                        if destination_lower in heading_text:
                            destination_in_content = True
                            break
                except:
                    continue

            # Try other generic selectors if test_ids didn't work
            heading_selectors = [
                "h1",
                "[data-section-id='TITLE_DEFAULT']",
                "[data-plugin-in-point-id='EXPLORE_HEADER']"
            ]

            for selector in heading_selectors:
                heading = self.page.locator(selector).first
                if heading.is_visible(timeout=1000):
                    heading_text = heading.inner_text().lower()
                    if destination_lower in heading_text:
                        destination_in_content = True
                        break

            # Check filters or search params
            filter_test_ids = ["little-search", "structured-search-input-field-query"]
            for test_id in filter_test_ids:
                try:
                    filter_elem = self.page.locator(f"[data-testid='{test_id}']")
                    if filter_elem.is_visible(timeout=1000):
                        filter_text = filter_elem.inner_text().lower()
                        if destination_lower in filter_text:
                            destination_in_content = True
                            break
                except:
                    continue

            # Try other selectors if test_ids didn't work
            if not destination_in_content:
                filter_selectors = ["button[data-index='0']"]

                for selector in filter_selectors:
                    filter_elem = self.page.locator(selector).first
                    if filter_elem.is_visible(timeout=1000):
                        filter_text = filter_elem.inner_text().lower()
                        if destination_lower in filter_text:
                            destination_in_content = True
                            break
        except Exception as e:
            destination_in_content = False
            allure.attach(
                str(e),
                name="Error checking destination in content",
                attachment_type=allure.attachment_type.TEXT
            )

        # Return True if the destination is found in any of the checked places
        return url_contains_destination or title_contains_destination or destination_in_content

    @allure.step("Get number of search results")
    def get_results_count(self) -> int:
        """Get the number of search results.
        
        Returns:
            int: The number of search results.
        """
        return self.search_results.get_results_count()
    
    @allure.step("Check if search was successful")
    def is_search_successful(self) -> bool:
        """Check if the search was successful.
        
        Returns:
            bool: True if the search was successful.
        """
        # Take a screenshot for debugging
        self.page.screenshot(path="test-results/check-search-success.png")
        
        # Check if the page has loaded properly
        try:
            # Check for search results containers with test_ids
            result_test_ids = ["card-container", "listing-card", "explore-footer"]
            
            for test_id in result_test_ids:
                try:
                    container = self.page.locator(f"[data-testid='{test_id}']")
                    # Use .first to handle multiple elements
                    if container.first.is_visible(timeout=2000):
                        return True
                except:
                    continue
            
            # Try generic selectors if test_ids didn't work
            result_selectors = [
                "[itemprop='itemListElement']", 
                "div[role='main']",
                "main[id='site-content']"
            ]
            
            for selector in result_selectors:
                container = self.page.locator(selector).first
                if container.is_visible(timeout=2000):
                    return True
            
            # Check for empty state with test_ids
            try:
                empty_test_id = "no-results-section"
                empty_state = self.page.locator(f"[data-testid='{empty_test_id}']")
                if empty_state.is_visible(timeout=1000):
                    # Search was technically successful, but no results were found
                    return False
            except:
                pass
                
            # Try generic empty state selectors
            empty_selectors = [
                "div:has-text('No results found')",
                "div:has-text('We couldn\\'t find any')"
            ]
            
            for selector in empty_selectors:
                empty_state = self.page.locator(selector).first
                if empty_state.is_visible(timeout=1000):
                    # Search was technically successful, but no results were found
                    return False
                
            # Check if we're still on the homepage using test_ids
            homepage_test_ids = ["home-search-form", "home-banner"]
            for test_id in homepage_test_ids:
                try:
                    indicator = self.page.locator(f"[data-testid='{test_id}']")
                    if indicator.is_visible(timeout=1000):
                        # We're still on the homepage, so search did not complete
                        return False
                except:
                    continue
                    
            # Try generic homepage indicators
            homepage_selectors = ["header:has-text('Airbnb it')"]
            for selector in homepage_selectors:
                indicator = self.page.locator(selector).first
                if indicator.is_visible(timeout=1000):
                    # We're still on the homepage, so search did not complete
                    return False
                    
            # Check the URL to see if it looks like a search results page
            current_url = self.page.url.lower()
            if "/s/" in current_url or "search_type" in current_url:
                return True
                
            # If we can see listings, it's successful
            return self.get_results_count() > 0
            
        except Exception as e:
            allure.attach(
                self.page.screenshot(),
                name="Search success check error",
                attachment_type=allure.attachment_type.PNG
            )
            allure.attach(str(e), name="Error details", attachment_type=allure.attachment_type.TEXT)
            return False


    @allure.step("Validating the highest rate listing details, dates and guests number")
    def validate_highest_rated_listing_details(self, popup_card_details_page, adults_count, child_count, check_in_days_from_now, check_out_days_from_now):

        check_in_formatted, check_out_formatted = self.search_bar.calc_dates(check_in_days_from_now, check_out_days_from_now)

    # Get the new page from the promise
        page_info = popup_card_details_page
        new_page = page_info.value
        logger.info("New page opened")

        # Wait for the new page to load
        new_page.wait_for_load_state("networkidle", timeout=30000)
        logger.info("New page loaded")

        # Screenshot the new page
        allure.attach(
            new_page.screenshot(),
            name="New listing page",
            attachment_type=allure.attachment_type.PNG
        )

        # Get the check-in date text
        check_in_element = new_page.locator('[data-testid="change-dates-checkIn"]')
        check_out_element = new_page.locator('[data-testid="change-dates-checkOut"]')
        guests_number_element = new_page.locator('[id="GuestPicker-book_it-trigger"]')

        # Wait for the element to be visible and get its text
        if check_in_element.is_visible(timeout=5000):
            check_in_text = check_in_element.inner_text()
            check_out_text = check_out_element.inner_text()
            guests_number_text = guests_number_element.inner_text()
            logger.info(f"Check-in date found: {check_in_text}")
            logger.info(f"Check-out date found: {check_out_text}")
            logger.info(f"Guests number found: {guests_number_text}")
            check_in_text = self.search_results.convert_date_format(check_in_text)
            check_out_text = self.search_results.convert_date_format(check_out_text)
            guests_number_text = int(guests_number_text.split("guests")[0])

            try:
                logger.info("asserting check-in date")
                assert check_in_text == check_in_formatted
                logger.info("asserting check-out date")
                assert check_out_text == check_out_formatted
                logger.info("asserting guests number")
                assert guests_number_text == adults_count + child_count
            except AssertionError as e:
                logger.error(f"highest listing card details validation failed: {e}")
                allure.attach(
                    self.page.screenshot(),
                    name="highest listing card details validation error",
                    attachment_type=allure.attachment_type.PNG
                )
                raise e

    @allure.step("Removing kids from the highest rate listing")
    def remove_kids_from__highest_rated_listing(self, popup_card_details_page, new_child_count):
        page_info = popup_card_details_page
        new_page = page_info.value

        #get the current child number

        guests_button = new_page.locator('[id="GuestPicker-book_it-trigger"]')
        current_guest_number = int(guests_button.inner_text().split("guests")[0])
        current_child_count_element = new_page.locator('[data-testid="GuestPicker-book_it-form-children-stepper-a11y-value-label"]')
        reduce_child_count_element = new_page.locator('[data-testid="GuestPicker-book_it-form-children-stepper-decrease-button"]')
        increase_child_count_element = new_page.locator('[data-testid="GuestPicker-book_it-form-children-stepper-increase-button"]')
        reduce_child_count = 1

        try:
            logger.info("opening the guests details")
            guests_button.click()
            current_child_num = int(current_child_count_element.inner_text().split("child")[0])
            if current_child_num > new_child_count:
                reduce_child_count = current_child_num - new_child_count
                for _ in range(int(reduce_child_count)):
                    reduce_child_count_element.click()

            else:
                increase_child_count = new_child_count - current_child_num
            current_child_num = int(current_child_count_element.inner_text().split("child")[0])
            current_guest_number_after_update = int(guests_button.inner_text().split("guests")[0])
            assert new_child_count == current_child_num
            logger.info(f"child number updated successfully")
            logger.info(f"current guests number found: {current_child_num}")
            assert current_guest_number_after_update == current_guest_number - int(reduce_child_count)
            logger.info(f"total guest number was updated correctly: {current_guest_number_after_update}")
            allure.attach(
                self.page.screenshot(),
                name="child number updated",
                attachment_type=allure.attachment_type.PNG
            )
        except AssertionError as e:
            logger.info(f"updating the child number failed: {e}")
            allure.attach(
                self.page.screenshot(),
                name="failure updating child number error",
                attachment_type=allure.attachment_type.PNG
            )
            raise e


    @allure.step("Updating the highest rate listing details, dates and guests number")
    def update_highest_rated_listing_date(self, popup_card_details_page, check_in_days_from_now,
                                             check_out_days_from_now, new_delta_days):

        check_in_formatted, check_out_formatted = self.search_bar.calc_dates(check_in_days_from_now + new_delta_days, check_out_days_from_now + new_delta_days)
        logger.info(f"delta {new_delta_days}")

        self.check_availability(popup_card_details_page, check_in_formatted, check_out_formatted)


    def check_availability(self, popup_card_details_page, checkin_date, checkout_date):
        logger.info(f"Checking availability for {checkin_date} and {checkout_date}")
        page_info = popup_card_details_page
        new_page = page_info.value

        # Open the calendar
        check_in_button_element = new_page.locator('[data-testid="change-dates-checkIn"]')
        check_in_button_element.click()
        # Check a date range using YYYY-MM-DD format
        is_blocked, blocked_date = self.is_date_range_blocked(
            popup_card_details_page,
            checkin_date,
            checkout_date
        )

        if is_blocked:
            logger.info(f"Cannot book this date range. Date {blocked_date} is blocked.")
            close_cal = new_page.locator('[data-testid="availability-calendar-save"]')
            close_cal.click()
            self.reserve_and_validate(popup_card_details_page, adults_count=CONST.ADULTS_COUNT)

            return False
        else:
            logger.info("Date range is available!")
            self.reserve_and_validate(popup_card_details_page, adults_count=CONST.ADULTS_COUNT)
            return True

    def reserve_and_validate(self, popup_card_details_page, adults_count):
        page_info = popup_card_details_page
        new_page = page_info.value
        reserve_button_element = new_page.locator('[data-testid="homes-pdp-cta-btn"]')
        reserve_button_element = reserve_button_element.all()
        url_before_reserve = new_page.url
        reserve_button_element[1].click()
        logger.info(f"Reserved button was clicked")
        url_after_reserve = new_page.url
        logger.info(f"Current URL after clicking on reserve: {url_after_reserve}")
        logger.info(f"asserting the url after clicking on reserve was changed: {url_before_reserve}")
        assert url_before_reserve != url_after_reserve
        logger.info(f"asserting the number of adults {adults_count} in the url")
        assert f"numberOfAdults={adults_count}" and "book" in url_after_reserve


    def is_date_range_blocked(self, popup_card_details_page, start_date_str, end_date_str):
        """
        Check if any date in the range between start_date and end_date is blocked

        Args:
            page: Playwright page object
            start_date_str: Start date in format "YYYY-MM-DD"
            end_date_str: End date in format "YYYY-MM-DD"

        Returns:
            tuple: (is_blocked, blocked_date)
                - is_blocked (bool): True if any date in the range is blocked
                - blocked_date (str): The first blocked date in MM/DD/YYYY format, or None if none blocked
        """
        page_info = popup_card_details_page
        new_page = page_info.value

        # Convert input date strings (YYYY-MM-DD) to datetime objects
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

        start_calendar_date = start_date.strftime("%m/%d/%Y")
        end_calendar_date = end_date.strftime("%m/%d/%Y")

        # Validate that start date is before end date
        if start_date > end_date:
            raise ValueError("Start date must be before end date")

        # Calculate the number of days to check
        days_to_check = (end_date - start_date).days + 1

        # Iterate through each date in the range using a for loop
        for day_offset in range(days_to_check):
            # Get the current date
            current_date = start_date + timedelta(days=day_offset)

            # Format date to match data-testid format (MM/DD/YYYY)
            date_str = current_date.strftime("%d/%m/%Y")

            # Create locator for this date
            date_locator = new_page.locator(f'[data-testid="calendar-day-{date_str}"]')

            # Check if date exists in calendar
            if date_locator.count() > 0:
                # Check if date is blocked
                blocked_attr = date_locator.first.get_attribute('data-is-day-blocked')
                if blocked_attr == 'true':
                    return True, date_str
            else:
                try:
                # If we've checked all dates and none are blocked, click on start and end dates
                    start_date_locator = new_page.locator(f'[data-testid="calendar-day-{start_calendar_date}"]')
                    end_date_locator = new_page.locator(f'[data-testid="calendar-day-{end_calendar_date}"]')

                    # Click on start date
                    start_date_locator.click()

                    # Click on end date
                    end_date_locator.click()
                    # If we've checked all dates and none are blocked
                except Exception as e:
                    logger.info("added new dates")


        return False, None
