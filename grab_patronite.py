import pandas as pd
import numpy as np

import time
import random

import urllib.request
import urllib.error

from bs4 import BeautifulSoup

from tqdm import trange

# do jakiego numeru ID profilu jedziemy?
MAX_PATRONITE_ID = 380000


def grab_page(patronite_id):
    '''
    Funkcja pobiera dane ze strony Patronite.pl o profilu o numerze patronite_id i zwraca jako data frame
    '''

    # budujemy urla strony
    page_url = f"https://patronite.pl/profil/{patronite_id}/patron"

    # zapytanie razem z UserAgent udającym rzeczywistą przeglądarkę na desktopie
    req = urllib.request.Request(page_url,
                                 headers={
                                     'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
                                 })

    # czy da się wczytać stronę?
    try:
        page = urllib.request.urlopen(req)
    except Exception as e:
        # zakomentowane, żeby nie psuć progress bara
        # print(f"\n{patronite_id}: {e}")
        return None

    # wczytanie strony i przerobienie na string
    page_doc = page.read().decode('utf-8')

    # parser HTMLa przez BeautifulSoup
    soup = BeautifulSoup(page_doc, 'html.parser')

    # nazwa usera - H1 na stronie
    user_name = soup.find_all("h1")[0].getText().strip()
    # jeśli username to "Patron" to najpewniej profil nie jest wypełniony - olewamy takie
    # TODO:
    # zweryfikować czy to ma sens
    if user_name == 'Patron':
        return None

    # od kiedy w Partonite?
    el = soup.find_all(
        "div", attrs={"class": "author__bio--joinDate"})[0].getText().strip()
    el = el.replace('W Patronite od ', "")
    el = time.strptime(el, "%d.%m.%Y")
    user_date = (el.tm_year, el.tm_mon, el.tm_mday)

    # tagi
    tags = soup.find("div", attrs={"class": "author__header--tags"})
    tags = tags = [t.getText().strip() for t in tags.children if len(t) > 1]
    tags = "|".join(tags)

    dct = {
        "id": patronite_id,
        "name": user_name,
        "registration_year": user_date[0],
        "registration_month": user_date[1],
        "registration_day": user_date[2],
        "patrons": np.NaN,
        "dotations_per_month": np.NaN,
        "total_dotations": np.NaN,
        "tags": tags
    }

    # ilu darczyńców, ile miesięcznie i ile łącznie?
    if soup.find("div", attrs={"class": "author__stats--wrapper"}) is not None:
        for elem in soup.find("div", attrs={"class": "author__stats--wrapper"}).children:
            if len(elem) > 1:

                ciag = elem.getText().strip().replace("\n", " ")
                if "łącznie" in ciag:
                    liczba = ciag.replace(" zł łącznie", "").replace(" ", "")
                    dct['total_dotations'] = float(liczba)

                if "miesięcznie" in ciag:
                    liczba = ciag.replace(
                        " zł miesięcznie", "").replace(" ", "")
                    dct['dotations_per_month'] = float(liczba)

                if "patronów" in ciag:
                    liczba = ciag.replace("patronów", "").replace(" ", "")
                    dct['patrons'] = int(liczba)

    return pd.DataFrame(dct, index=[0])


if __name__ == "__main__":
    # ramka na zebrane dane
    full_df = pd.DataFrame()

    for i in trange(MAX_PATRONITE_ID):
        # grabujemy stronę o konkretnym ID
        temp_df = grab_page(i)

        # jeśli się udało - dodajemy do pełnej ramki
        if temp_df is not None:
            full_df = full_df.append(temp_df)

        # co 50 IDków zapisujemy plik tymczasowy, żeby w razie konieczności nie zaczynać od początku
        if i % 50 == 0:
            full_df.to_pickle(f"data/new_{i:04d}.pkl")

        # chwilę czekamy
        time.sleep(random.choice([0.25, 0.5, 0.75, 1]))

    # zapisujemy pełne dane
    full_df.drop_duplicates().to_pickle("data/new_all.pkl")
    print("\n\n=== FINISHED! ===")
    print("Saved to file data/new_all.pkl")
