import requests
import requests_random_user_agent
import time
from datetime import  datetime
from bs4 import BeautifulSoup

BASE_URL = "https://www.amazon.com.mx"

def scrapWhishlistUrls(whishlist_url: str):
    current_session = requests.session()
    urls = set()
    failed_attempts_left = 10
    while(True):
        if failed_attempts_left == 0:
            print(whishlist_url)
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
                    if left_panel:
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

def scrapeProdPage(prod_url: str,session:requests.Session)->dict:
    req = session.get(prod_url)
    err_out = open("err_.html","wb")
    err_out.write(req.content)

    if req.status_code == 200:
        soup = BeautifulSoup(req.text, "html.parser")
        name_span = soup.find("span", {"id": "productTitle"})
        if not name_span:
            print(f"[{datetime.now()}] Expired link ({prod_url})")
            return {"error":"Expired link"}
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
    else:
        print(f"[{datetime.now()}] Error status code: {req.status_code} {prod_url}")
        return {"error":"Network error"}


def main():
    print("This scripts is not supposed to be executed unless you wan't to try something outside the bot itself")
    # print (result)


if __name__ == "__main__":
    main()
