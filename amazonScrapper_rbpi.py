import requests
import time
from datetime import  datetime
from bs4 import BeautifulSoup

BASE_URL = "https://www.amazon.com.mx"



def scrapWhishlistUrls(whishlist_url: str, hdrs: dict ):
    current_session = requests.session()
    current_session.headers = hdrs
    urls = set()
    failed_attempts_left = 10
    while(True):
        if failed_attempts_left == 0:
            print(f"[{datetime.now()}] Error req/res")
            return set()
        if whishlist_url == None:
            return urls
        req = current_session.get(whishlist_url)
        if req.status_code == 200:
            soup = BeautifulSoup(req.text, "html.parser")
            whishlist = soup.find(id="g-items")
            if whishlist != None:
                for prod in whishlist.find_all("li"):
                    left_panel = prod.find(
                        "div", {"class": "a-fixed-left-grid-inner"})
                    left_panel = left_panel.find(
                        "div", {"class": "a-fixed-left-grid-inner"})
                    prod_url = left_panel.find("a", {"class": "a-link-normal"})
                    urls.add(prod_url['href'].split("&")[0])
                whishlist_url = _nextWhishlistSegment(soup)
            else:
                failed_attempts_left -= 1
        else:
            failed_attempts_left -= 1
        time.sleep(2)

def _nextWhishlistSegment(soup:BeautifulSoup):
    eol = soup.find("div",{"id":"endOfListMarker"})
    if eol==None:
        next_seg = soup.find("a", class_='wl-see-more')
        next_seg = BASE_URL+str(next_seg['href'])
        if next_seg:
            return  next_seg
        else:
            print(f"[{datetime.now()}] Couldnt find next segment of whishlist")
    
    

    
def scrapeProdPage(prod_url: str, hdrs: dict)->dict:
    req = requests.get(prod_url, headers=hdrs)
    if req.status_code == 200:
        soup = BeautifulSoup(req.text, "html.parser")
        price_box = soup.find("div", {"class": "a-box-group"})
        if price_box:
            try:
                price_span = price_box.find("span", {"id": "price"})
                if not price_span:
                    div_core = price_box.find("div",{"id":"corePrice_feature_div"})
                    price_span =div_core.find("span",{"class":"a-offscreen"})
                price = str(price_span.text).replace("$", "")
                price = price.replace(",", "")
                name_span = soup.find("span", {"id": "productTitle"})
                name = str(name_span.text)
                return {"name":name,"price":float(price)}
            except Exception as e:
                print(e.args)
                print(f"[{datetime.now()}] Not able to parse price ({prod_url})")
                return {"error":"Not able to parse"}
        else:
            print(f"[{datetime.now()}] Not available ({prod_url})")
            return {"error":"Not available"}

    else:
        print(f"[{datetime.now()}] Error status code: {req.status_code} {prod_url}")
        return {"error":"Network error"}


def main():
    print("This scripts is not supposed to be executed unless you wan't to try something outside the bot itself")
    # scrapProdPage("https://www.amazon.com.mx/Sennheiser-Aud%C3%ADfonos-abiertos-estereof%C3%B3nicos-profesionales/dp/B00004SY4H")
    # result = scrapWhishlistUrls("https://www.amazon.com.mx/hz/wishlist/ls/EB767EYMKQE5?ref_=wl_share")
    # print (result)


if __name__ == "__main__":
    main()
