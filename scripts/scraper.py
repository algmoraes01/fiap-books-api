import requests
from bs4 import BeautifulSoup
import pandas as pd
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

base_url = "https://books.toscrape.com/catalogue/page-{}.html"
books = []

session = requests.Session()

for page in range(1, 51):
    url = base_url.format(page)
    response = session.get(url, verify=False, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")
    items = soup.select("article.product_pod")

    for item in items:
        title = item.h3.a["title"]
        price = item.select_one("p.price_color").text.strip()
        availability = item.select_one("p.instock.availability").text.strip()
        rating = item.p["class"][1]
        image = "https://books.toscrape.com/" + item.img["src"].replace("../", "")

        link_rel = item.h3.a["href"]
        link = "https://books.toscrape.com/catalogue/" + link_rel.replace("../../", "").replace("../", "")
        book_page = session.get(link, verify=False, timeout=10)
        book_soup = BeautifulSoup(book_page.text, "html.parser")
        category = book_soup.select("ul.breadcrumb li a")[2].text.strip()

        books.append({
            "title": title,
            "price": price,
            "availability": availability,
            "rating": rating,
            "category": category,
            "image": image
        })

df = pd.DataFrame(books)
df.to_csv("data/books.csv", index=False, encoding="utf-8-sig")
