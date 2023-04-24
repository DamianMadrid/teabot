from matplotlib.font_manager import json_dump
import requests
import requests_random_user_agent
import json
from datetime import datetime
import sys
from bs4 import BeautifulSoup

BASE_URL = "https://www.ikea.com"


def scrapeProdPage(prod_url: str) -> dict:
    req_se = requests.Session()
    response = req_se.get(prod_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        prod_pip = soup.find("div", {"class": "product-pip"})
        nav_script = soup.find("script", {"id": "nav-script-common"})
        client_id = nav_script["data-client-id"]
        prod_id = prod_pip.attrs["data-product-id"]
        if prod_pip:
            prod_info = req_se.options(
                f"https://api.ingka.ikea.com/cia/availabilities/ru/mx?itemNos={prod_id}&expand=StoresList,Restocks,SalesLocations")
            print(prod_info.text)
        return {"name":"ph","price":"ph"}
    else:
        print(f"[{datetime.now()}] Error req/res [{prod_url}]")
        return {"error": "Network error"}


def main():
    print("This scripts is not supposed to be executed unless you wan't to try something outside the bot itself")
    res = scrapeProdPage(
        "https://www.ikea.com/mx/en/p/lisabo-table-ash-veneer-70294339/")

    print(res)


if __name__ == "__main__":
    main()
