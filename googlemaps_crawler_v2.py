from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException
from typing import Union
from urllib import parse

# Fully matched: 直接搜尋到目標頁面，可以看得到Business data。
# Highly matched: 搜尋頁面會列出多個搜尋結果，我們預設抓第一個結果。
# Low matched: 搜尋頁面顯示[部分符合的結果]，同樣會列出搜尋結果，但非常少(可能只有一筆)。
# No matched: 找不到任何結果。

# Definition of constants
BASE_URL = "https://www.google.com.tw/maps/search/"
PAGE_BRANCH_SELECTORS = {
    # get_attribute("href")
    "search_highly_matched": "div[aria-label$=搜尋結果][role=\"feed\"] a:nth-child(1)",
    # get_attribute("href")
    "search_low_matched": "div[aria-label$=搜尋結果][role=\"feed\"] a:nth-child(1)"
}
_RELATIVE_INFO_TARGET_BLOCK = "div[class=\"m6QErb \"][role=\"region\"][aria-label$=\"相關資訊\"]"
TARGET_ELEMENT_SELECTORS = {
    "name": "div[role=\"main\"] h1[class=\"DUwDvf fontHeadlineLarge\"]",
    "rating": "div[role=\"main\"] div[class=\"F7nice \"] span:nth-child(1) span:nth-child(1)",
    "total_reviews": "div[role=\"main\"] div[class=\"F7nice \"] span:nth-child(1) span[aria-label]:nth-child(1)",
    "place_type": "button[class=\"DkEaL \"]",
    # get_attribute("aria-label")
    "address": f"{_RELATIVE_INFO_TARGET_BLOCK} button[class=\"CsEnBe\"][aria-label^=\"地址\"][data-item-id=\"address\"]",
    # get_attribute("aria-label")
    "website": f"{_RELATIVE_INFO_TARGET_BLOCK} a[class=\"CsEnBe\"][aria-label^=\"網站\"][data-item-id=\"authority\"]",
    # get_attribute("aria-label")
    "phone_number": f"{_RELATIVE_INFO_TARGET_BLOCK} button[class=\"CsEnBe\"][aria-label^=\"電話號碼\"]",
    # used to find the drop-down button, we need to click on it
    "opening_hours": "div[class=\"OMl5r hH0dDd jBYmhd\"][data-hide-tooltip-on-mouse-move=\"true\"][aria-expanded=\"false\"][role=\"button\"]"
}
# total 7 elements
OPENING_HOURS_ELEMENT_ITEMS_SELECTOR = "table[class^=\"eK4R0e\"] tbody tr[class=\"y0skZc\"]"
OPENING_HOURS_ITEM_WEEK_ELEMENT_SELECTOR = "table[class^=\"eK4R0e\"] tbody tr[class=\"y0skZc\"] td[class^=\"ylH6lf \"] div"
OPENING_HOURS_ITEM_DURATION_ELEMENT_SELECTOR = "table[class^=\"eK4R0e\"] tbody tr[class=\"y0skZc\"] td[class=\"mxowUb\"] li[class=\"G8aQO\"]"

BUSINESS_DATA_FIELDS = ("name", "rating", "total_reviews", "place_type", "address", "website", "phone_number", "opening_hours")


class CustomCondition:
    class get_business_elements:
        def __init__(self, data: dict):
            self.data = data

        def __call__(self, driver) -> bool:
            """
            Find elements to update data dictionary
            """
            for field in BUSINESS_DATA_FIELDS[:4]:
                if self.data[field] is None:
                    try:
                        ele = driver.find_element(By.CSS_SELECTOR, TARGET_ELEMENT_SELECTORS[field])
                        self.data[field] = ele.text
                    except NoSuchElementException:
                        pass
            for field in BUSINESS_DATA_FIELDS[4:4+3]:
                if self.data[field] is None:
                    try:
                        ele = driver.find_element(By.CSS_SELECTOR, TARGET_ELEMENT_SELECTORS[field])
                        self.data[field] = ele.get_attribute("aria-label")
                    except NoSuchElementException:
                        pass

            # handle opening hours
            # 在此之前必須操控selenium點開營業時間的標籤，否則抓不到資料
            try:
                drop_down_ele = driver.find_element(By.CSS_SELECTOR, TARGET_ELEMENT_SELECTORS["opening_hours"])
                # 找到之後滾動頁面到該元素位置，確認它可以被selenium看到
                action = ActionChains(driver)
                action.move_to_element(drop_down_ele).perform()
                drop_down_ele.click()
            except NoSuchElementException:
                pass
            except ElementNotInteractableException:
                pass
            # 抓opening_hours資料
            try:
                ele_list = driver.find_elements(By.CSS_SELECTOR, OPENING_HOURS_ELEMENT_ITEMS_SELECTOR)
                for ele in ele_list:
                    week = ele.find_element(By.CSS_SELECTOR, OPENING_HOURS_ITEM_WEEK_ELEMENT_SELECTOR).text
                    durations = ele.find_elements(By.CSS_SELECTOR, OPENING_HOURS_ITEM_DURATION_ELEMENT_SELECTOR)
                    if week not in self.data["opening_hours"] and week.strip():
                        self.data["opening_hours"][week] = "/".join([e.text for e in durations])
            except NoSuchElementException:
                pass

            # check all fields were found
            if all(self.data.values()):
                return True
            return False

    class get_branch_url:
        """
        Find branch url of first search result.
        """
        def __call__(self, driver) -> Union[str, bool]:
            try:
                ele = driver.find_element(By.CSS_SELECTOR, PAGE_BRANCH_SELECTORS["search_highly_matched"])
                return ele.get_attribute("href")
            except NoSuchElementException:
                try:
                    ele = driver.find_element(By.CSS_SELECTOR, PAGE_BRANCH_SELECTORS["search_low_matched"])
                    return ele.get_attribute("href")
                except NoSuchElementException:
                    return False


class GoogleMapsBusinessCrawler:
    def __init__(self):
        self.driver = webdriver.Edge()

    def __del__(self):
        self.driver.quit()

    def __fully_matched_case(self, timeout: int) -> Union[dict, bool]:
        """
        The page shows correct contents which we want.
        :param timeout: timeout seconds
        :return: data dictionary if any field was found successfully else False
        """
        data = {k: None for k in BUSINESS_DATA_FIELDS}
        data["opening_hours"] = {}  # init value of opening hours is an empty dict
        try:
            WebDriverWait(self.driver, timeout).until(CustomCondition.get_business_elements(data))
        except TimeoutException:
            pass
        if any(data.values()):
            return data
        return False

    def __partially_matched_case(self, timeout: int) -> Union[str, bool]:
        try:
            url = WebDriverWait(self.driver, timeout).until(CustomCondition.get_branch_url())
            return url
        except TimeoutException:
            return False

    def get_business(self, search_keywords: list):
        self.driver.get(BASE_URL + " ".join(search_keywords))

        # Try partially matched case first
        search_result_url = self.__partially_matched_case(1)

        if search_result_url:
            # Branch to the place page if current page is on search result page
            self.driver.get(search_result_url)

        # Try fully matched case if current page is on the place page
        data = self.__fully_matched_case(2)
        if isinstance(data, dict):
            data["map"] = parse.unquote(self.driver.current_url)  # 轉換網址編碼來縮短長度
            return data
        return False


if __name__ == "__main__":
    crawler = GoogleMapsBusinessCrawler()
    print(crawler.get_business(["宏亞食品巧克力觀光工廠", "33451 桃園縣八德市建國路386號"]))
