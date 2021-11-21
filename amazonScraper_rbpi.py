#Date and time
import time
from datetime import datetime
# Data scraping
import bs4
from bs4.element import ResultSet
import requests
# Data wrangling
import pandas as pd
from math import isnan
# Path 
import os 


# Requests headers

#hdrs = {"User agent": "Mozilla/5.0 (Windows NT 10.0Win64x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36"}
idDict = {
    'tab': 'my-lists-tab',
    'items': 'g-items',
    'load_more': 'wl-see-more',
    'end': 'endOfListMarker'}
# Miscellaneous
loading = ['/', '|', '\\']
current_exec = ""

AMAZONURL = "https://www.amazon.com.mx"
# PATH
PATH_WHISHLISTS =os.path.join(os.path.expanduser("~"),"YARAPT/data/whishlists.csv")
PATH_PRICES_DATA = os.path.join(os.path.expanduser("~"),"YARAPT/data/prices_data.csv")



def awaitConnection()->bool:
    for i in range(10):
        try:
            req_session.get(AMAZONURL, timeout=1)
            return True
        except:
            time.sleep(1)
            continue
        break
    return False

meta_col = "url,name,price,goal,category,last_seen,lowest,highest".split(",")
req_session = requests.Session()

def getPage(url: str):
    global req_session
    try:
        page = req_session.get(url)
        soup = bs4.BeautifulSoup(page.content, 'html.parser')
        return soup
    except requests.ConnectionError:
        return
    return

def isEndOfList(page):
    is_end = page.find(id=idDict['end'])
    #print("is end:",is_end)
    if(is_end):
        return True
    return False


def retrieveAmazonData(wl_url, path):
    global AMAZONURL
    global current_exec
    global alerter
    df: pd.DataFrame = pd.read_csv(path, index_col="url")
    currBlock = wl_url
    while(True):
        time.sleep(1)
        # Retrieve wishlist
        page = getPage(AMAZONURL+currBlock)
        # print(currBlock)
        if page == None:
            #print("page is ",  page)
            return False
        #print("page returned not none")
        whishlist = page.find(id=idDict['items'])
        #print(whishlist)
        if whishlist != None:
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
            currBlock = page.find("a", class_=idDict['load_more'])
            try:
                currBlock = currBlock['href']
            except:
                print(page)
                return False
        else:
            break
    # Save data
    df.to_csv(PATH_PRICES_DATA, index="url")
    return True


def dataInfo(path, save=False)->str:
    global current_exec
    alert_message = {}
    # Setting the plot props
    df: pd.DataFrame = pd.read_csv(
        path, index_col="url", dtype={'last_seen': 'object'})
    for url, data in df.iterrows():
        current_price = data.at[current_exec]
        if not isnan(current_price):
            # General update
            alert_message[url] = {"name":data['name'],"content":""}
            df.at[url, "last_seen"] = current_exec
            if data.lowest > current_price or pd.isna(data.lowest):
                df.at[url, "lowest"] = current_price
                alert_message[url]["content"]= f"⏬{current_price:.2f}\n"
            # Check if available again
            if pd.isna(data["last_seen"]):
                alert_message[url]["content"]+= f"📦{current_price:.2f}\n"
            if data.highest < current_price or pd.isna(data.highest):
                df.at[url, "highest"] = current_price
            if data.goal > current_price:
                alert_message[url]["content"]= f"🏁{current_price:.2f}\n"
            # Calculate change in price
            else:
                if pd.notna(data["last_seen"]): 
                    last_price = data[data["last_seen"]]
                    priceDelta = last_price - current_price
                    is_disccout = priceDelta > 0
                    priceDelta = abs(priceDelta)
                    # Bigger than 10%
                    if priceDelta > last_price * .1:
                        alert_message[url]["content"]+= f"{'🟢' if is_disccout else '🔴'} {last_price} -> {current_price:.2f}\n"
    df.to_csv(PATH_PRICES_DATA)
    final_message = ''
    for key, val in alert_message.items():
        if val["content"]!="":
            final_message+=f'{val["name"]}\n     {val["content"]}'
    return final_message



def generate_Update():
    global current_exec
    current_exec = str(datetime.now())
    if not awaitConnection():
        return "await connection error"
    # Get whislist list
    wishlists_df = pd.read_csv(PATH_WHISHLISTS, index_col="url")
    # Start scrapping
    for url, name in wishlists_df.iterrows():
        if not retrieveAmazonData(url, PATH_PRICES_DATA):
            return f"cannot retrieve {name} "
    return dataInfo(PATH_PRICES_DATA)


def main():
    print("This scripts is not supposed to be executed unless you wan't to try something outside the bot itself")
    print("Entering into debugging mode")
    test_str = generate_Update()
    print(test_str)

if __name__ == "__main__":
    main()
