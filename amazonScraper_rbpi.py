#Date and time
import time
from datetime import datetime
import sys
# Data scraping
import bs4
import requests
# Data wrangling
import numpy as np
import pandas as pd
from math import isnan, nan
from collections import Counter
from alerts import Mail_alert


# Requests headers
hdrs = {
    "User agent": "Mozilla/5.0 (Windows NT 10.0Win64x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36"}
idDict = {
    'tab': 'my-lists-tab',
    'items': 'g-items',
    'load_more': 'wl-see-more',
    'end': 'endOfListMarker'}
# Miscellaneous
loading = ['/', '|', '\\']

current_exec = str(datetime.now())

AMAZONURL = "https://www.amazon.com.mx"
# PATH
PATH_WHISHLISTS = "./whishlists.csv"
PATH_PRICES_DATA = "./prices_data.csv"


def awaitConnection():
    i = 0
    while(True):
        try:
            requests.get(AMAZONURL, headers=hdrs, timeout=.2)
        except:
            i = (i+1) % 3
            time.sleep(1)
            continue
        break
    return


meta_col = "url,name,price,goal,category,last_seen,lowest,highest".split(",")


def getPage(url: str):
    try:
        page = requests.get(url, headers=hdrs)
        soup = bs4.BeautifulSoup(page.content, 'html.parser')
        return soup
    except requests.ConnectionError:
        print('Could not connect. Try again when connected')
        sys.exit()
    return


def isEndOfList(page):
    if(page.find(id=idDict['end'])):
        return True
    return False


def retrieveAmazonData(wl_url, path):
    global AMAZONURL
    global current_exec
    global alerter
    df: pd.DataFrame = pd.read_csv(path, index_col="url")
    currBlock = wl_url
    while(True):
        # Retrieve wishlist
        page = getPage(AMAZONURL+currBlock)
        whishlist = page.find(id=idDict['items'])
        if whishlist == None:
            print("Cannot get items from whishlist")
            print(page)
            sys.exit()
            return
        for child in whishlist.find_all("li"):
            priceData = child.find('span', {"class": "a-offscreen"})
            if priceData != None:
                title_tag = child.find('h3').find('a')
                price = priceData.contents[0][1:].replace(',', '')
                url = title_tag['href'][0:14]
                df.at[url, current_exec] = price
                df.at[url, "name"] = title_tag['title'][0:20]
        # Check for end of list
        if(not isEndOfList(page)):
            currBlock = page.find("a", class_=idDict['load_more'])['href']
        else:
            break
    # Save data
    df.to_csv(PATH_PRICES_DATA, index="url")
    return


def dataInfo(path, save=False):
    global current_exec
    # Setting the plot props
    df: pd.DataFrame = pd.read_csv(
        path, index_col="url", dtype={'last_seen': 'object'})
    for url, data in df.iterrows():
        current_price = data.at[current_exec]
        if not isnan(current_price):
            # General update
            alerter.addToAlert(url, data['name'])
            df.at[url, "last_seen"] = current_exec
            if data.lowest > current_price or pd.isna(data.lowest):
                df.at[url, "lowest"] = current_price
                alerter.addContent(url,
                                   f"(LOWEST) is at: {current_price}!\n")
            if data.highest < current_price or pd.isna(data.highest):
                df.at[url, "highest"] = current_price
            if data.goal > current_price:
                alerter.addToAlert(
                    f"(GOAL) is at: {current_price}!\n")
            # Check if available again
            if pd.isna(data["last_seen"]):
                alerter.addToAlert(
                    f"(RESTOCK) is available again: {current_price}\n")
            # Calculate change in price
            else:
                last_price = data[data["last_seen"]]
                priceDelta = last_price - current_price
                is_disccout = priceDelta > 0
                priceDelta = abs(priceDelta)
                # Bigger than 10%
                if priceDelta > last_price * .1:
                    alerter.addToAlert(
                        f"Price is {'DOWN' if is_disccout else 'UP'} by {priceDelta}\n")
    df.to_csv("prices_data.csv")


if __name__ == '__main__':
    global alerter
    alerter = Mail_alert()
    # Check for connection
    awaitConnection()
    # Get whislist list
    wishlists_df = pd.read_csv(PATH_WHISHLISTS, index_col="url")
    # Start scrapping
    for url, name in wishlists_df.iterrows():
        # time.sleep(5)
        retrieveAmazonData(url, PATH_PRICES_DATA)
    dataInfo(PATH_PRICES_DATA)
    alerter.printAlerts()
