import time
import sqlite3
import re
from datetime import datetime, timedelta
from typing import Optional
from requests import Session
from selenium import webdriver
from selenium.webdriver import FirefoxOptions as Options
import scrapper.amazonScrapper_rbpi as amazon
import scrapper.liverpoolScraper_rbpi as liverpool
from enum import Enum
REXP = r'\d{4}-\d{2}-\d{2}'


class Domain(Enum):
    NONE = 0
    LIVERPOOL = 1
    AMAZON_MX = 2


class Scrapper:
    def __init__(self, data_path: str) -> None:
        if data_path[-1] == "/":
            data_path = data_path[:-1]
        self._initDatabases(data_path)
        self.driver_opt = Options()
        self.driver_opt.add_argument("--headless") 
        self._renewSession()
        pass

    def _initDatabases(self,data_path:str)->None:
        self.pricesDB = sqlite3.connect(
            data_path+"/prices.db", check_same_thread=False,)
        cur = self.pricesDB.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS prices (\
                    URL TEXT PRIMARY KEY,\
                    DOMAIN INTEGER,\
                    NAME TEXT,\
                    CURRENT_PRICE REAL,\
                    LAST_PRICE REAL,\
                    GOAL REAL,\
                    LOWEST REAL ,\
                    HIGHEST REAL);")
        self.pricesDB.commit()

    def _renewSession(self) -> None:
        self.session = Session()
        self.session.headers.update(
            {"accept-language": "en-US,en;q=0.9,ja-JP;q=0.8,ja;q=0.7,es-419;q=0.6,es;q=0.5"}) 
        self.driver = webdriver.Firefox(options= self.driver_opt)
        self.driver.get(amazon.BASE_URL)
        return

    def _getDomainURL(self, domain_val: int) -> str:
        domain = Domain(domain_val)
        if domain == Domain.LIVERPOOL:
            return "liverpool.com"
        if domain == Domain.AMAZON_MX:
            return "amazon.com.mx"

    def _identifyDomain(self, url: str) -> Domain:
        if "liverpool.com" in url:
            return Domain.LIVERPOOL
        if "amazon.com.mx" in url:
            return Domain.AMAZON_MX
        return Domain.NONE

    def _stripURL(self, prod_url: str, domain=None) -> str | None:
        if domain == None:
            domain = self._identifyDomain(prod_url)
        if domain == Domain.AMAZON_MX:
            striped_url = re.search(r"\/(dp|gp)(.*\/)?", prod_url)
            if (not striped_url is None):
                return "".join(striped_url.groups())
        if domain == Domain.LIVERPOOL:
            striped_url = prod_url.split(".mx")[-1]
            return striped_url
        return None

    def scrapeProd(self, url: str, domain_val: int, curr_session: Session) -> dict:
        domain = Domain(domain_val)
        if domain == Domain.AMAZON_MX:
            return amazon.scrapeProdPage(amazon.BASE_URL+ "/"+ url, self.driver, curr_session)
        if domain == Domain.LIVERPOOL:
            return liverpool.scrapeProdPage(liverpool.BASE_URL + url, curr_session)
        return {"error": "unexpected error, couldnt identify domain"}

    def removeProd(self, url: str) -> bool:
        try:
            self.pricesDB.execute("DELETE FROM PRICES WHERE URL = ?", (url,))
            self.pricesDB.commit()
            return True
        except Exception as e:
            print("Exception in remove prod")
            print(e)
            return False

    def addProd(self, prod_url: str, domain: Domain | None = None, goal: float = 0) -> bool:
        if domain == None:
            domain = self._identifyDomain(prod_url)
        prod_url = self._stripURL(prod_url, domain)
        if domain == Domain.NONE:
            return False
        _prodInDb = self.pricesDB.execute(
            "SELECT * FROM PRICES WHERE URL = ?", [prod_url])
        if len(_prodInDb.fetchall()):
            return False
        try:
            print(prod_url, goal, domain.value)
            self.pricesDB.execute(
                "INSERT INTO PRICES(URL, GOAL, DOMAIN) VALUES (?,?,?)", (prod_url, goal, domain.value))
            self.pricesDB.commit()
            return True
        except Exception as e:
            print("Exception in addProd")
            print(e)
            return False

    

    def pruneOldData(self, current_exec):
        # Get all columns
        cols = self.pricesDB.execute(
            "select name from pragma_table_info('prices')").fetchall()
        # Filter those that are dates
        date_columns = list(filter(lambda _col: re.match(REXP, _col[0]), cols))
        date_columns = [datetime.strptime(x[0], '%Y-%m-%d') for x in date_columns]
        limit_date = datetime.today() - timedelta(days=300)
        date_columns_to_delete = list(filter(lambda _date: _date<limit_date, date_columns))
        date_columns_to_delete = [(str(x.date()),) for x in date_columns_to_delete]
        # Delete old columns
        for date_col in date_columns_to_delete:
            self.pricesDB.execute(f"alter table prices drop column [{date_col[0]}] ")
        self.pricesDB.commit()

    def addDateColumn(self, current_exec: str):
        cols = self.pricesDB.execute(
            "select name from pragma_table_info('prices')").fetchall()
        cols = [c[0] for c in cols]
        if not current_exec in cols:
            self.pruneOldData(current_exec=current_exec)
            self.pricesDB.execute(
                f"alter table prices add column [{current_exec}];")
            self.pricesDB.commit()
        return

    def updateSavedProd(self, current_exec: str):
        error_prod = []
        current_session = Session()
        self.addDateColumn(current_exec)
        for  url, domainval, current_price in self.pricesDB.execute("SELECT url,domain,current_price FROM PRICES").fetchall():
            print(f"Scrapping {url,domainval}")
            new_data: dict = self.scrapeProd(url, domainval, current_session)
            print(new_data)
            if "error" in new_data:
                print(new_data["error"])
                if new_data["error"] == "Expired link":
                    print(f"[{datetime.now()}] Removed ({url})")
                    self.removeProd(url)
                error_prod.append({"url": url, "error": new_data["error"]})
            else:
                self.pricesDB.execute(f"update prices set name = ?,\
                    last_price = ?, current_price = ?,\
                    [{current_exec}] = ? where url = ?",
                    (new_data["name"].strip(),
                    current_price, new_data["price"],
                    new_data["price"], url))
            time.sleep(2)
        self.pricesDB.commit()
        if len(error_prod):
            update_str = "⚠️ The next items couldn't be updated\n"
            for error_p in error_prod:
                update_str += f"{error_p['error']}\n"
        return

    def updateString(self, current_exec: str):
        cur = self.pricesDB.execute(
            "SELECT URL,DOMAIN,NAME,CURRENT_PRICE,LAST_PRICE,GOAL,LOWEST,HIGHEST FROM PRICES")
        alert_message = dict()
        for  url, domain, name, current_price, last_price, goal, lowest, highest in cur.fetchall():
            if current_price:
                # General update
                alert_message[url] = {"name": str(name).strip(
                ), "content": "", "price": current_price, "domain": self._getDomainURL(domain)}
                if not lowest or lowest > current_price:
                    self.pricesDB.execute("UPDATE PRICES SET LOWEST = ?, GOAL = ? WHERE url = ?", (
                        current_price, current_price-1, url))
                    alert_message[url]["content"] = f"⏬"
                # Check if available again
                if not last_price:
                    alert_message[url]["content"] += f"📦"
                if not highest or highest < current_price:
                    self.pricesDB.execute(
                        "UPDATE PRICES SET HIGHEST  = ? WHERE url = ?", (current_price, url))
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
                self.pricesDB.execute(
                    "UPDATE PRICES SET LAST_PRICE = ? WHERE URL  = ?", (current_price, url))
        final_message = ''
        self.pricesDB.commit()
        for url, val in alert_message.items():
            if val["content"] != "":
                final_message += f'[<a href="{val["domain"]+url}">{val["name"][:18]}</a>]\n{val["content"]} : {val["price"]:.2f}\n'
        return final_message

if __name__ == "__main__":
    print("This file is not meant to be executed individually")
    pass
