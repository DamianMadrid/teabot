import requests
import requests_random_user_agent
import json
from datetime import datetime
import sys
from bs4 import BeautifulSoup



BASE_URL ="https://www.liverpool.com.mx" 

def searchKeyword(keyword: str):
    r = requests.get(
        f"https://www.liverpool.com.mx/typeahead?query={keyword}&type=all")
    try:
        urls = [prod["url"] for prod in r.json()["products"]]
    except:
        return ''
    return urls


def scrapeProdPage(prod_url: str,curr_session:requests.Session)->dict:
    req = curr_session.get(prod_url)
    if req.status_code == 200:
        soup = BeautifulSoup(req.text, "lxml")
        script_json_data = soup.find("script", {"id": "__NEXT_DATA__"})
        json_data_str = str(script_json_data.string)
        prod_data = json.loads(json_data_str)
        variants = prod_data["query"]["data"]["mainContent"]["records"][0]["allMeta"]["variants"]
        if len(variants) == 0:
            print(f"[{datetime.now()}] Se encontró el producto, pero no las variantes ")
            return -1
        minPrice = sys.maxsize+1
        if not len(variants):
            return {"error":"Unavailable"}
        for var in variants:
            for price in var["prices"]:
                if "price" in str(price).lower() :
                    name = var["skuName"]
                    minPrice= min(float(var["prices"][price]),minPrice)
        return {"name":name,"price":minPrice}
    else:
        print(f"[{datetime.now()}] Error req/res [{prod_url}]")
        return {"error":req.status_code}


def main():
    print("This scripts is not supposed to be executed unless you wan't to try something outside the bot itself")
    res = scrapeProdPage("https://www.liverpool.com.mx/tienda/pdp/Piano-digital-Casio-Celviano-AP-470-negro/1083747664")
    print(res)

if __name__ == "__main__":
    main()
