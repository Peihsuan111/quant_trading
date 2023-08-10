"""
Crawling stock price from 證交所
"""
import datetime
import json
from pymongo import MongoClient
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
import time


def driver_setup(headless=True):
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    if headless:
        chrome_options.add_argument('--headless')
    path = 'chromedriver'
    driver = webdriver.Chrome(executable_path=path, options=chrome_options)
    return driver


def setup_page(driver, chosn_yr, chosn_mt):
    # Input ticker
    ticker_input = driver.find_element(
        By.CLASS_NAME, "stock-code-autocomplete")
    ticker_input.clear()
    ticker_input.send_keys(ticker)
    # Choose time
    yr_dropdwn = Select(driver.find_element(By.ID, 'label0'))
    yr_dropdwn.select_by_value(chosn_yr)
    parent_ele = driver.find_element(By.ID, 'label0')
    mt_dropdwn = Select(parent_ele.find_element(
        By.XPATH, f"following-sibling::select[1]"))
    mt_dropdwn.select_by_value(chosn_mt)
    # Submit
    driver.find_element(
        By.XPATH, '//*[@id="form"]/div/div[1]/div[3]/button').click()
    time.sleep(3)
    return driver


def connect2db(data_to_insert):
    with open("./config.json") as f:
        config_info = json.load(f)
        db_config = config_info["local_db"]
    client = MongoClient(db_config["client"],
                         username=db_config["username"],
                         password=db_config["password"],
                         authSource='admin',
                         authMechanism='SCRAM-SHA-256')
    db = client['finance']
    collection = db['stocks']
    result = collection.insert_many(data_to_insert)
    return result


driver = driver_setup(False)
twse_web = 'https://www.twse.com.tw/zh/trading/historical/stock-day.html'
driver.get(twse_web)
time.sleep(2)

ticker = "2330"
# Scrape data
dic = dict()

# chosn_yr = "2022"
for chosn_yr in ["2020", "2021", "2022"]:
    for chosn_mt in range(1, 9):
        print(f'process | year:{chosn_yr} month:{chosn_mt}')
        driver = setup_page(driver, chosn_yr, str(chosn_mt))
        table_elem = driver.find_element(
            By.XPATH, '//*[@id="reports"]/div[2]/div[2]/table').get_attribute('innerHTML')
        tdata = BeautifulSoup(table_elem, "html.parser")
        for tr in tdata.find("tbody").find_all('tr'):
            tmp_ls = []
            for td in tr.find_all('td'):
                tmp_ls.append(td.text)
            dic[tmp_ls[0]] = tmp_ls[1:]

# Insert into mongod
# Replace 'mongodb://localhost:27017/' with your MongoDB connection string
data_to_insert = []
for k, v in dic.items():
    y, m, d = [int(i) for i in k.split('/')]
    date_date = datetime.datetime(y+1911, m, d)
    to_ins = {
        'ticker': ticker,
        'date': date_date,
        'volumn': int(v[0].replace(',', '')),
        'total_amount': int(v[1].replace(',', '')),
        'open': float(v[2].replace(',', '')),
        'high': float(v[3].replace(',', '')),
        'low': float(v[4].replace(',', '')),
        'close': float(v[5].replace(',', '')),
        'spread': float(v[6].replace(',', '').replace('X', '')),
        'turnover': int(v[7].replace(',', ''))
    }
    data_to_insert.append(to_ins)

connect2db(data_to_insert)

# import csv
# with open('2330.csv', 'w') as csvfile:
#     writer = csv.writer(csvfile)
#     for x in data_to_insert:
#             writer.writerow([x['ticker'],x['date'].strftime('%Y-%m-%d'), x['volumn'],x['total_amount'],x['open'], x['high'], x['low'], x['close'], x['spread'], x['turnover']])
