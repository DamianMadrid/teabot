from datetime import datetime, timedelta
import time
from typing import Optional, Union, final
import sqlite3
import re
from requests import request, Session
import amazonScrapper_rbpi as amazon
import liverpoolScraper_rbpi as liverpool
from enum import Enum


class Domain(Enum):
    NONE = 0
    LIVERPOOL = 1
    AMAZON_MX = 2

class FromWishList(Enum):
    notfromwishlist = 0
    fromwishlist = 1

def _getDomainURL(domain_val:int)->str:
        domain = Domain(domain_val)
        if domain  == Domain.LIVERPOOL:
            return "liverpool.com"
        if domain == Domain.AMAZON_MX:
            return "amazon.com.mx"

class Scrapper:
    def _getDomainURL(self,domain_val:int)->str:
        domain = Domain(domain_val)
        if domain  == Domain.LIVERPOOL:
            return "liverpool.com"
        if domain == Domain.AMAZON_MX:
            return "amazon.com.mx"

    def __init__(self, path: str) -> None:
        if path[-1] == "/":
            path = path[:-1]
        self.db_con = sqlite3.connect(path+"/prices.db", check_same_thread=False)
        self.wldb = sqlite3.connect(path+"/wl.db",check_same_thread=False)
        pass

    def _identifyDomain(self, url: str) -> Domain:
        if "liverpool.com" in url:
            return Domain.LIVERPOOL
        if "amazon.com.mx" in url:
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

    def scrapeProd(self, url: str, domain_val: int,curr_session:Session) -> dict:
        domain = Domain(domain_val)
        if domain == Domain.AMAZON_MX:
            return amazon.scrapeProdPage(amazon.BASE_URL+ url,curr_session)
        if domain == Domain.LIVERPOOL:
            return liverpool.scrapeProdPage(liverpool.BASE_URL+ url,curr_session)
        return {"error":"unexpected error, couldnt identify domain"}

    def removeProd(self, id: str) -> bool:
        try:
            self.db_con.execute("DELETE FROM PRICES WHERE PROD_ID = ?",(id,))
            self.db_con.commit()
            print()
            return True
        except Exception as e:
            print("Exception in remove prod")
            print(e)
            return False

    def addProd(self, prod_url: str, domain:Optional[Domain] =  None, goal: float = 0, fromwl:int = 0) -> bool:
        if domain == None:
            domain = self._identifyDomain(prod_url)
            prod_url = self._stripURL(prod_url,domain)
        if domain == Domain.NONE:
            return False
        indb = self.db_con.execute("SELECT * FROM PRICES WHERE URL = ?",[prod_url] )
        if len(indb.fetchall()):
            return False
        try:
            self.db_con.execute("INSERT INTO PRICES(URL, GOAL, DOMAIN,FROMWISHLIST) VALUES (?,?,?,?)",(prod_url,goal,domain.value,fromwl))
            self.db_con.commit()
            return True
        except Exception as e:
            print("Exception in addProd")
            print(e)
            return False

    def checkWishList(self)->str:
        saved_urls = set( [row for row, in  self.db_con.execute("select url from prices").fetchall()])
        new_prods = set()
        for wl_url, in self.wldb.execute("select url from wishlists").fetchall():
            urls_from_wl = amazon.scrapWhishlistUrls(amazon.BASE_URL+ wl_url)
            for url in urls_from_wl:
                url = self._stripURL(url,Domain.AMAZON_MX)
                if url in saved_urls:
                    saved_urls.remove(url)
                else:
                    new_prods.add(url)
                    self.addProd(url,domain=Domain.AMAZON_MX,fromwl=FromWishList.fromwishlist.value)
        # Wich products are added to the df if any
        update_str = ""
        if len(new_prods):
            update_str += "📥 The next items have been added \n"
            for new_p in new_prods:
                update_str += f"\t{new_p} \n"
        # See which products from wishlist should be removed
        removed_url = set()
        for unseen_url in saved_urls:
            unseen_id,unseen_domain,unseen_name,unseen_fwl = self.db_con.execute("SELECT PROD_ID,DOMAIN,NAME, FROMWISHLIST FROM PRICES WHERE URL = ?", (unseen_url,)).fetchone()
            if unseen_domain == Domain.AMAZON_MX.value and unseen_fwl == FromWishList.fromwishlist.value:
                self.removeProd(unseen_id)
                removed_url.add(unseen_url)
        if len(removed_url):
            update_str = "✂️The next items have been removed\n"
            for removed_p in removed_url:
                update_str += f"[{unseen_name[:15]}]\n"
        if update_str == "":
            update_str  = "No updates 👍"
        return(update_str)

    def pruneOldData(self,current_exec):
        pass


    def addDateColumn(self,current_exec:str):
        cols  = self.db_con.execute("select name from pragma_table_info('prices')").fetchall()
        cols = [c[0] for c in cols]
        prune_Date=None
        if not current_exec in cols:
            prune_Date = (datetime.now()-timedelta(90)).date()
            self.db_con.execute(f"alter table prices add column [{current_exec}];")
        if prune_Date and prune_Date in cols:
            try:
                self.db_con.execute(f"alter table drop column [{prune_Date}];")
            except Exception  :
                pass
        return

    def updateSavedProd(self, current_exec:str):
        current_session = Session()
        current_session.headers.update({"accept-language": "en-US,en;q=0.9,ja-JP;q=0.8,ja;q=0.7,es-419;q=0.6,es;q=0.5"})
        error_prod = []
        self.addDateColumn(current_exec)
        for prod_id,url,domainval,current_price in self.db_con.execute("SELECT prod_id,url,domain,current_price FROM PRICES").fetchall():
            new_data:dict = self.scrapeProd(url ,domainval,current_session)
            print(new_data)
            if "error" in new_data:
                print(new_data["error"])
                if new_data["error"]=="Expired link":
                    print(f"[{datetime.now()}] Removed ({url})")
                    self.removeProd(prod_id)
                error_prod.append({"url":url, "error":new_data["error"]})
            else:
                self.db_con.execute(f"update prices set name = ?,\
                     last_price = ?, current_price = ?,\
                     [{current_exec}] = ? where prod_id = ?",
                     (new_data["name"].strip(),
                     current_price,new_data["price"],
                     new_data["price"],prod_id))
            time.sleep(2)
        self.db_con.commit()
        if len(error_prod):
            update_str = "⚠️ The next items couldn't be updated\n"
            for error_p in error_prod:
                update_str += f"{error_p['error']}\n"
        return


    def updateString(self, current_exec:str):
        cur = self.db_con.execute("SELECT PROD_ID,URL,DOMAIN,NAME,CURRENT_PRICE,LAST_PRICE,GOAL,LOWEST,HIGHEST FROM PRICES")
        alert_message = dict()
        for prod_id,url,domain,name,current_price,last_price,goal,lowest,highest in cur.fetchall():
            if current_price:
                # General update
                alert_message[url] = {"name":str(name).strip(), "content": "","price":current_price,"domain":self._getDomainURL(domain)}
                if not lowest or lowest > current_price:
                    self.db_con.execute("UPDATE PRICES SET LOWEST = ?, GOAL = ? WHERE PROD_ID = ?",(current_price,current_price-1,prod_id))
                    alert_message[url]["content"] = f"⏬"
                # Check if available again
                if not last_price  :
                    alert_message[url]["content"] += f"📦"
                if not highest or highest < current_price :
                    self.db_con.execute("UPDATE PRICES SET HIGHEST  = ? WHERE PROD_ID = ?",(current_price,prod_id))
                if goal and goal > current_price:
                    alert_message[url]["content"] = f"🏁"
                # Calculate price change
                else:
                    if last_price:
                        priceDelta = last_price - current_price
                        is_disccout = priceDelta > 0
                        priceDelta = abs(priceDelta)
                        # Bigger than 20%
                        if priceDelta > last_price * .2:
                            alert_message[url]["content"] += f"{'🟢' if is_disccout else '🔴'}"
#            self.db_con.execute("UPDATE PRICES SET LAST_PRICE = ? WHERE PROD_ID = ?",(current_price,prod_id))
        final_message = ''
        for url, val in alert_message.items():
            if val["content"] != "":
                final_message += f'[<a href="{val["domain"]+url}">{val["name"][:18]}</a>]\n{val["content"]} : {val["price"]:.2f}\n'
        return final_message


def main():
    current_exec  = str(datetime.now().date())
    test_scrapper = Scrapper("./data/")
    update_message = test_scrapper.updateSavedProd(current_exec)
    print(update_message)
    
    # files = {'f': ('err_.html', open('err_.html', 'rb'))}
    # response = current_session.get("https://www.amazon.com.mx/dp/B016P9HJIA",files=files)
    # response.raise_for_status() # ensure we notice bad responses
    # with open("resp_text.txt", "w") as file:
    #     file.write(response.text)
    # print(res)


if __name__ == "__main__":
    main()
