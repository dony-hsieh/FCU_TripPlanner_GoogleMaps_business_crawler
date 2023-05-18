import json
import re
import copy
from datetime import datetime

from googlemaps_crawler_v2 import GoogleMapsBusinessCrawler
from database import Database
from definitions import CRAWLED_BUSINESS_DATA_FIELDS, CRAWLED_DATA_STORE_PATH

DAY_MAPPING = {"星期一": "1", "星期二": "2", "星期三": "3", "星期四": "4", "星期五": "5", "星期六": "6", "星期日": "7"}

# {
#   V 'name': '宏亞食品工廠',
#   V 'rating': '4.0',
#   V 'total_reviews': '(306)',
#   V 'place_type': '食品供應商',
#     'address': '地址: 334桃園市八德區建國路386號 ',
#   V 'website': '網站: hunya.com.tw ',
#     'phone_number': '電話號碼: 03 368 5055 ',
#   V 'opening_hours': {
#         '星期日': '休息',
#         '星期一': '09:30–12:30/14:00–17:30',
#         '星期二': '09:30–12:30/14:00–17:30',
#         '星期三': '09:30–12:30/14:00–17:30',
#         '星期四': '09:30–12:30/14:00–17:30',
#         '星期五': '09:30–12:30/14:00–17:30',
#         '星期六': '休息'
#     },
#   V 'map': 'https://www.google.com.tw/maps/place/宏亞食品工廠/@24.9401053,121.2881995,17z/data=!3m1!4b1!4m6!3m5!1s0x346818eaf8fba1f7:0xc4dd98d5bf069e7e!8m2!3d24.9401053!4d121.2881995!16s/g/1w6r5_zs'
# }

# Steps:
# 1. 先從資料庫抓出所有景點(attraction)的id, name、zipcode、add。
# 2. 迭代所有景點:
#   a. 將[name, zipcode, add]輸入Crawler抓資料。
#   b. 將資料寫入一個csv檔
# 3. 將csv檔中的資料更新到資料庫中。


def multiple_replace(text: str, replace_dict: dict):
    rep = dict((re.escape(k), v) for k, v in replace_dict.items())
    pattern = re.compile("|".join(rep.keys()))
    return pattern.sub(lambda m: rep[re.escape(m.group(0))], text)


def get_all_attractions(db: Database) -> list:
    statement = "SELECT `Id`, `Name`, `Zipcode`, `Add` FROM `Attraction`;"
    return list(db.execute_R(statement))


def crawl_business_data(attractions: list) -> list:
    def remove_none(s: str): return s if s is not None else ""
    crawler = GoogleMapsBusinessCrawler()
    business_data_list = []
    for attraction_row in attractions:
        keywords = [remove_none(word) for word in attraction_row[1:]]
        business_data = crawler.get_business(keywords)
        business_row = {"Id": attraction_row[0]}
        business_row.update({field: business_data.get(field, None) for field in CRAWLED_BUSINESS_DATA_FIELDS})
        parse_business_data(business_row)
        business_data_list.append(business_row)
    return business_data_list


def parse_business_data(business_row: dict):
    if business_row["total_reviews"] is not None:
        business_row["total_reviews"] = multiple_replace(business_row["total_reviews"], {"(": "", ")": "", ",": ""})
    if business_row["website"] is not None:
        business_row["website"] = business_row["website"].split(":")[-1].strip()
    # parse opening hours
    # 1. 原本的是 {"星期一": "09:30-17:00", "星期二": "09:30-17:00", ...}
    #    -> 變成 {1: [{"open": "09:30", "close": "17:00"}], 2: [{"open": "09:30", "close": "17:00"}], ...}
    # 2. 原本的是 {"星期二": "09:30-12:30/14:00-17:30", "星期三": "09:30-12:30/14:00-17:30", ...}
    #    -> 變成 {2: [{"open": "09:30", "close": "12:30"}, {"open": "14:00", "close": "17:30"}], 3: [{"open": "09:30", "close": "12:30"}, {"open": "14:00", "close": "17:30"}], ...}
    if business_row["opening_hours"]:
        data_dict = {}
        pattern = r"\d{2}:\d{2}"
        for k, v in business_row["opening_hours"].items():
            period_dict_list = []
            period_str_list = [p.strip() for p in v.split("/")]  # 分割出時間段字串，最少一個 ("09:30–17:00")
            for period_str in period_str_list:
                matched_list = re.findall(pattern, period_str)
                if len(matched_list) == 2:
                    period_dict_list.append({"open": matched_list[0], "close": matched_list[1]})
                elif "24" in period_str and "小時營業" in period_str:
                    period_dict_list.append({"open": "00:00", "close": "24:00"})
                else:
                    period_dict_list.append(period_str)
            data_dict[DAY_MAPPING[k]] = period_dict_list
        business_row["opening_hours"] = copy.deepcopy(data_dict)  # copy or assign reference?


def store_json(fp: str, data):
    with open(fp, mode="w", encoding="utf-8") as f:
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        f.write(json_str)


if __name__ == "__main__":
    db = Database()
    filename = datetime.strftime(datetime.now(), "%Y%m%d_%H%M%S_test.json")

    attractions = get_all_attractions(db)
    data = crawl_business_data(attractions[:10])
    store_json(f"{CRAWLED_DATA_STORE_PATH}/{filename}", data)
