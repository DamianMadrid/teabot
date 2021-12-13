import time
from math import isnan
from typing import Union
import re
import amazonScrapper_rbpi as amazon
import liverpoolScraper_rbpi as liverpool
import pandas as pd
from enum import Enum


default_hdrs = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36",
    'Accept-Language': 'en-US, en;q=0.5'}

class Domain(Enum):
    NONE = 0
    LIVERPOOL = 1
    AMAZON_MX = 2


class FromWishList(Enum):
    notfromwishlist = 0
    fromwishlist = 1
    

class Scrapper:
    def __init__(self, path: str,headers = default_hdrs) -> None:
        if path[-1] == "/":
            path = path[:-1]
        self.data_path = path+"/prices_data.csv"
        self.whishlist_path = path+"/wishlists.csv"
        self.headers = headers
        pass

    def _identifyDomain(self, url: str) -> Domain:
        if "liverpool.com" in url:
            return Domain.LIVERPOOL
        if "amazon.com" in url:
            return Domain.AMAZON_MX
        return Domain.NONE

    def _stripURL(self, prod_url: str, domain = None)->Union[str,None]:
        if domain == None:
            domain = self._identifyDomain(prod_url)
        if domain == Domain.AMAZON_MX:
            striped_url = re.search(r"\/dp\/(.*)\/", prod_url)
            if len(striped_url.groups()) == 1:
                return striped_url.group(0)[:-1]
        if domain == Domain.LIVERPOOL:
            striped_url = prod_url.split(".mx")[-1]
            return striped_url
        return None

    def scrapeProd(self, url: str, domain_val: int) -> dict:
        domain = Domain(domain_val)
        if domain == Domain.AMAZON_MX:
            return amazon.scrapeProdPage(amazon.BASE_URL+ url,self.headers)
        if domain == Domain.LIVERPOOL:
            return liverpool.scrapeProdPage(liverpool.BASE_URL+ url,self.headers)
        return {"error":"unexpected error, couldnt identify domain"}

    def removeProd(self, prod_url: str) -> bool:
        try:
            df = pd.read_csv(self.data_path, index_col="url")
            df = df.drop(prod_url)
            df.to_csv(self.data_path)
            return True
        except Exception as e:
            return False

    def addProd(self, prod_url: str, goal: float = 0) -> bool:
        domain = self._identifyDomain(prod_url)
        prod_url = self._stripURL(prod_url,domain)
        if domain == Domain.NONE:
            return False
        try:
            df = pd.read_csv(self.data_path, index_col="url")
            df.at[prod_url, "goal"] = goal
            df.at[prod_url, "domain"] = domain.value
            df.to_csv(self.data_path)
            return True
        except Exception as e:
            return False
    

    def checkWishList(self)->str:
        prices_df = pd.read_csv(self.data_path, index_col="url")
        wl_df = pd.read_csv(self.whishlist_path, index_col="url")
        saved_urls = set(prices_df.index)
        new_prods = set()
        # Check which url are aready in the df 
        for wl_url,wl_name in wl_df.iterrows():
            urls_from_wl = amazon.scrapWhishlistUrls(amazon.BASE_URL+ wl_url,self.headers)
            for url in urls_from_wl:
                url = self._stripURL(url,Domain.AMAZON_MX)
                if url in saved_urls:
                    saved_urls.remove(url)
                else:
                    new_prods.add(url)
                    prices_df.at[url,"domain"]=Domain.AMAZON_MX.value
                    prices_df.at[url,"fromWishlist"]=FromWishList.fromwishlist.value
        # Wich products are added to the df if any
        update_str = ""
        if len(new_prods):
            update_str += "📥 The next items have been added \n"
            for new_p in new_prods:
                update_str += f"\t{new_p} \n"
        # See which products from wishlist should be removed
        removed_url = set()
        for unseen_url in saved_urls:
            if prices_df.at[unseen_url,"domain"] == Domain.AMAZON_MX.value and prices_df.at[unseen_url,"fromWishlist"] == FromWishList.fromwishlist.value:
                prices_df =  prices_df.drop(unseen_url)
                removed_url.add(unseen_url)
                
        if len(removed_url):
            update_str = "✂️The next items have been removed\n"
            for removed_p in removed_url:
                update_str += f"\t{removed_p} \n"
        prices_df.to_csv(self.data_path)
        if update_str == "":
            update_str  = "No updates 👍"
        return(update_str)

    def updateSavedProd(self, current_exec:str):
        prices_df = pd.read_csv(self.data_path, index_col="url")
        error_prod = []
        for url, prod in prices_df.iterrows():
            print(url)
            new_data:dict = self.scrapeProd(url ,prod["domain"])
            if "error" in new_data:
                error_prod.append({"url":url, "error":new_data["error"]})
            else:
                prices_df.at[url,"name"] = new_data["name"]
                prices_df.at[url,current_exec] = new_data["price"]
                prices_df.at[url,"last_seen"] = current_exec
            time.sleep(1)

        if len(error_prod):
            update_str = "⚠️ The next items couldn't be updated\n"
            for error_p in error_prod:
                update_str += f"\{error_p['url']}:{error_p['error']} \n"
        prices_df.to_csv(self.data_path)

                


    def updateString(self, current_exec:str):
        df: pd.DataFrame = pd.read_csv(
        self.data_path, index_col="url", dtype={'last_seen': 'object'})

        alert_message = dict()
        for url, data in df.iterrows():
            current_price = data.at[current_exec]
            if not isnan(current_price): 
                # General update
                alert_message[url] = {"name": data['name'], "content": ""}
                if data.lowest > current_price or pd.isna(data.lowest):
                    df.at[url, "lowest"] = current_price
                    df.at[url, "goal"] = current_price
                    alert_message[url]["content"] = f"⏬{current_price:.2f}\n"
                # Check if available again
                if pd.isna(data["last_seen"]):
                    alert_message[url]["content"] += f"📦{current_price:.2f}\n"
                if data.highest < current_price or pd.isna(data.highest):
                    df.at[url, "highest"] = current_price
                if data.goal > current_price:
                    alert_message[url]["content"] = f"🏁{current_price:.2f}\n"
                # Calculate price change
                else:
                    if pd.notna(data["last_seen"]):
                        last_price = data[data["last_seen"]]
                        priceDelta = last_price - current_price
                        is_disccout = priceDelta > 0
                        priceDelta = abs(priceDelta)
                        # Bigger than 20%
                        if priceDelta > last_price * .2:
                            alert_message[url]["content"] += f"{'🟢' if is_disccout else '🔴'} {last_price} is now {current_price:.2f}\n"
        df.to_csv(self.data_path)
        final_message = ''
        for key, val in alert_message.items():
            if val["content"] != "":
                final_message += f'{val["name"]}\n     {val["content"]}'
        return final_message


def main():
    pass
    # my_scrapper = Scrapper("./data/")

    # my_scrapper.updateSavedProd()
    
    


if __name__ == "__main__":
    main()
