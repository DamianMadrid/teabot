import time
from requests import Session
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from datetime import  datetime
from bs4 import BeautifulSoup

BASE_URL = "https://www.amazon.com.mx"

def scrapWhishlistUrls(whishlist_url: str,driver:webdriver):
    urls = set()
    try:
        driver.get(whishlist_url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "g-items"))
        )
        soup = BeautifulSoup(driver.page_source,"lxml")
        whishlist = soup.find(id="g-items")
        if whishlist != None:
            for prod in whishlist.find_all("li"):
                left_panel = prod.find(
                    "div", {"class": "a-fixed-left-grid-inner"})
                if left_panel:
                    left_panel = left_panel.find(
                        "div", {"class": "a-fixed-left-grid-inner"})
                    prod_url = left_panel.find("a", {"class": "a-link-normal"})
                    urls.add(prod_url['href'].split("&")[0])
            whishlist_url = _nextWhishlistSegment(soup)
        return urls
    except TimeoutException:
        print(whishlist_url)
        print(f"[{datetime.now()}] Error req/res")
        return set()

def _nextWhishlistSegment(soup:BeautifulSoup):
    eol = soup.find("div",{"id":"endOfListMarker"})
    if eol==None:
        next_seg = soup.find("a", class_='wl-see-more')
        next_seg = BASE_URL+str(next_seg['href'])
        if next_seg:
            return  next_seg
        else:
            print(f"[{datetime.now()}] Couldnt find next segment of whishlist")

def scrapeProdPage(prod_url: str,driver:webdriver,session:Session)->dict:
    driver.get(prod_url)
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "productTitle"))
        )
        soup = BeautifulSoup(driver.page_source,"lxml")
        name_span = soup.find("span", {"id": "productTitle"})
        name = str(name_span.text).strip()
        price_box = soup.find("div", {"class": "a-box-group"})
        if price_box:
            try:
                price_span = price_box.find("span", {"id": "price"})
                if not price_span:
                    div_core = price_box.find("div",{"id":"corePrice_feature_div"})
                    price_span =div_core.find("span",{"class":"a-offscreen"})
                price = str(price_span.text).replace("$", "")
                price = price.replace(",", "")
                return {"name":name,"price":float(price)}
            except Exception as e:
                print(e.args)
                print(f"[{datetime.now()}] Not availble ({prod_url})")
                return {"error":"Not available"}
        else:
            try:
                price_span = soup.find("span", {"class": "a-size-base a-color-price"})
                price = str(price_span.text).replace("$", "")
                price = price.replace(",", "")
                return {"name":name,"price":float(price)}
            except Exception as e:
                print(e.args)
                print(f"[{datetime.now()}] Not able to parse price ({prod_url})")
                return {"error":"Not able to parse"}
    except TimeoutException:
        print(f"[{datetime.now()}] Couldn't find productTitle {prod_url}")
        return {"error":"Network error"}


def main():
    print("This scripts is not supposed to be executed unless you wan't to try something outside the bot itself")


if __name__ == "__main__":
    main()
