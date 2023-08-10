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
import datetime
from dateutil import relativedelta
import requests

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

def load_page():
    driver = driver_setup(False)
    web = 'https://www.twse.com.tw/zh/trading/historical/stock-day.html'
    driver.get(web)
    time.sleep(2)
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

def request_go(ticker, start, end):
    """_summary_

    Args:
        ticker (str): _description_
        start (str): dataset from. example. 2023-01
        end (str): dataset to. example. 2023-01
    """
    # Scrape data
    dic = dict()
    st_y, st_m = start.split("-")
    ed_y, ed_m = end.split("-")
    start_dt = datetime.date(int(st_y),int(st_m),1)
    end_dt = datetime.date(int(ed_y),int(ed_m),1)
    delta = relativedelta.relativedelta(end_dt, start_dt)
    diff_mth = delta.years * 12 + delta.months
    chosn_time = list()
    for x in range(diff_mth+1):
        chosn_time.append((start_dt + relativedelta.relativedelta(months=x)).strftime('%Y%m%d'))

    # (A)using requests
    for date_str in chosn_time:
        print(date_str)
        api = "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?date={}&stockNo={}&response=json".format(date_str, ticker)
        r = requests.get(api)
        data = r.json()
        for x in data['data']:
            dic[x[0]] = x[1:]

    # prepare to insert data
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
    return data_to_insert

def selenium_go(ticker, chosn_yr, mth_ls):
    """_summary_

    Args:
        ticker (str): _description_
        yr (str): year. example. "2023"
        mth_ls (list): list of month. example. [1,2,3,4,5]
    """
    driver = load_page()

    # Scrape data
    dic = dict()
    
    # (B)using selenium
    for chosn_mt in mth_ls:
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

    # prepare to insert data
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
    return data_to_insert


ticker = "2454"

# (A) to db
connect2db(data_to_insert)

# (B) to csv
import csv
with open("./data/"+ticker+'.csv', 'a') as csvfile:
    writer = csv.writer(csvfile)
    for x in data_to_insert:
            writer.writerow([x['ticker'],x['date'].strftime('%Y-%m-%d'), x['volumn'],x['total_amount'],x['open'], x['high'], x['low'], x['close'], x['spread'], x['turnover']])
