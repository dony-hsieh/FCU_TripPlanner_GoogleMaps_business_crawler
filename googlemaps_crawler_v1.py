from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException


class GoogleMapsRatingScrawler:
    BEGIN_URL = "https://www.google.com.tw/maps"
    XPATHS = {
        "MULTI_SEARCH_RES": {
            "LISTED":          "//*[@id=\"QA0Szd\"]/div/div/div[1]/div[2]/div/div[1]/div/div/div[2]/div[1]/div[1]/div/a",
            "PARTIALLY_MATCH": "//*[@id=\"QA0Szd\"]/div/div/div[1]/div[2]/div/div[1]/div/div/div[2]/div[2]/div[2]/div/a"
        },
        "SINGLE_SEARCH_RES": {
            "NAME":   "//*[@id=\"QA0Szd\"]/div/div/div[1]/div[2]/div/div[1]/div/div/div[2]/div/div[1]/div[1]/h1",
            "RATING": "//*[@id=\"QA0Szd\"]/div/div/div[1]/div[2]/div/div[1]/div/div/div[2]/div/div[1]/div[2]/div/div[1]/div[2]/span[1]/span[1]",
            "ADDR": {
                "UPPER":       "//*[@id=\"QA0Szd\"]/div/div/div[1]/div[2]/div/div[1]/div/div/div[7]/div[3]/button/div/div[3]/div[1]",
                "LOWER":       "//*[@id=\"QA0Szd\"]/div/div/div[1]/div[2]/div/div[1]/div/div/div[9]/div[3]/button/div/div[3]/div[1]",
                "LOWER_HOTEL": "//*[@id=\"QA0Szd\"]/div/div/div[1]/div[2]/div/div[1]/div/div/div[11]/div[3]/button/div/div[3]/div[1]"
            }
        }
    }

    def __init__(self):
        self.driver = webdriver.Edge()

    def __del__(self):
        self.driver.quit()

    def locate_visible_element(self, timeout: int, locator: tuple):
        ele = None
        try:
            ele = WebDriverWait(self.driver, timeout).until(EC.visibility_of_element_located(locator))
        except TimeoutException as error:
            ele = None
            print("[*] Locating visible element failed")
        finally:
            return ele

    def locate_clickable_element(self, timeout: int, locator: tuple):
        ele = None
        try:
            ele = WebDriverWait(self.driver, timeout).until(EC.element_to_be_clickable(locator))
        except TimeoutException as error:
            ele = None
            print("[*] Locating clickable element failed")
        finally:
            return ele

    def __single_search(self):
        """
        :return: tuple(Name, Rating, Address) or False if all searching were failed
        """
        ret = []
        name_ele = self.locate_visible_element(10, (By.XPATH, self.XPATHS["SINGLE_SEARCH_RES"]["NAME"]))
        if name_ele is not None:
            ret.append(name_ele.text)
        else:
            ret.append("")

        rating_ele = self.locate_visible_element(10, (By.XPATH, self.XPATHS["SINGLE_SEARCH_RES"]["RATING"]))
        if rating_ele is not None:
            ret.append(rating_ele.text)
        else:
            ret.append("")

        addr_ele = self.locate_visible_element(10, (By.XPATH, self.XPATHS["SINGLE_SEARCH_RES"]["ADDR"]["UPPER"]))
        if addr_ele is None:
            addr_ele = self.locate_visible_element(10, (By.XPATH, self.XPATHS["SINGLE_SEARCH_RES"]["ADDR"]["LOWER"]))
        if addr_ele is not None:
            ret.append(addr_ele.text)
        else:
            ret.append("")

        if not any(ret):
            return False
        return tuple(ret)

    def get_rating(self, search_input: str):
        """
        :param search_input: Search text
        :return: tuple(Name, Rating, Address) or False if all searching were failed
        """
        # open search page
        self.driver.get(f"{self.BEGIN_URL}/search/{search_input}")

        # Try single search first
        info = self.__single_search()
        if not info:
            # Try multi search results
            listed_res_ele = self.locate_clickable_element(10, (By.XPATH, self.XPATHS["MULTI_SEARCH_RES"]["LISTED"]))
            if listed_res_ele is not None:
                self.driver.get(listed_res_ele.get_attribute("href"))
                return self.__single_search()
            listed_res_ele = self.locate_clickable_element(10, (By.XPATH, self.XPATHS["MULTI_SEARCH_RES"]["PARTIALLY_MATCH"]))
            if listed_res_ele is not None:
                self.driver.get(listed_res_ele.get_attribute("href"))
                return self.__single_search()
            # Searching failed or all conditions were time out
            print("[*] Failed to get rating")
            return None
        return info


if __name__ == "__main__":
    # 部分相符: "八二三紀念公園(中和公園)" + " 新北市235中和區中安街、安樂路、安平路及永貞路間"
    # addr麻煩: "水璉、牛山海岸", "花蓮縣974壽豐鄉牛山39之5號"]
    scrawler = GoogleMapsRatingScrawler()
    search_keywords = ["牛山呼庭休閒園區民宿", "花蓮縣壽豐鄉水璉村牛山39-5號"]
    search_text = " ".join(search_keywords)
    info = scrawler.get_rating(search_text)
    print(f"[*] Search: Keywords: {str(search_keywords)}; Results: {str(info)}")
