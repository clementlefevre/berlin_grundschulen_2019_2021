#!/usr/bin/env python
# coding: utf-8


import requests
from lxml import etree
import pandas as pd
import time
from multiprocessing import Pool
import glob

NUM_PROCS = 20

years_range = range(10, 20)
start = ["20" + str(y).zfill(2) for y in years_range]
end = [str(y + 1).zfill(2) for y in years_range]
start_end_list = list(zip(start, end))
start_end_list[0]

df_schools_url_all = pd.read_csv("schools_list.csv")


path = r"data/"
all_files = glob.glob(path + "/*.csv")
li = []
for filename in all_files:
    df = pd.read_csv(filename, index_col=0)
    li.append(df)

try:
    df_current_data = pd.concat(li, axis=0, ignore_index=True)
    last_current_schoolNr = df_current_data.iloc[-1].School_Nr
    index_of_last_current_schoolNr = df_schools_url_all.loc[
        df_schools_url_all.SchulNr == last_current_schoolNr
    ].index[0]
    df_schools_url = df_schools_url_all.iloc[index_of_last_current_schoolNr:]
except:
    df_schools_url = df_schools_url_all
    df_current_data = pd.DataFrame()


df_schools_url = df_schools_url[["SchulNr", "Name", "url"]]
schools = df_schools_url.to_dict(orient="records")
print("starting with : ", schools[0])


BASE_URL = "https://www.berlin.de/sen/bildung/schule/berliner-schulen/schulverzeichnis/schuelerschaft.aspx?view="
ndh_urls = [
    BASE_URL + "ndh&jahr=" + start_end[0] + "/" + start_end[1]
    for start_end in start_end_list
]

urls_title = [y[0] + "/" + y[1] for y in start_end_list]
ndh_urls = list(zip(urls_title, ndh_urls))


def get_ndh(session, url):
    try:
        r = session.get(url[1])

        tree = etree.HTML(r.text)
        school_name = tree.xpath(
            '//span[@id="ContentPlaceHolderMenuListe_lblUebSchule"]/text()'
        )
        school_name = school_name[0]

        df_year = pd.read_html(r.text, decimal=",", thousands=".")[0]
        if 0 not in df_year.columns.values:
            df_year.columns = df_year.columns.droplevel(0)
            # pandas 0.18.0 and higher
            df_year = df_year.rename_axis(None, axis=1)
            df_year.columns = [
                "Insgesamt",
                "Schülerinnen",
                "Schüler",
                "Insgesamt.1",
                "Insg. in %",
            ]
            df_year["year"] = str(url[0])

            return df_year
    except Exception as e:
        print(e)
        return None


def get_ndh_all_years(session):
    df = pd.DataFrame()
    for url in ndh_urls:
        time.sleep(2)
        df_year = get_ndh(session, url)
        if df_year is not None:
            df = pd.concat([df, df_year], axis=0)

    return df


def get_school_data(school):
    print(school)
    time.sleep(2)
    session = requests.Session()
    r = session.get(school["url"])
    tree = etree.HTML(r.text)
    school_type=""
    try:
        school_type = tree.xpath(
        '//span[@id="ContentPlaceHolderMenuListe_lblSchulart"]/text()'
    )
        school_type = school_type[0]
    except :
        pass

    df_school_data = get_ndh_all_years(session)
    df_school_data["School_Nr"] = school["SchulNr"]
    df_school_data["Name"] = school["Name"]
    df_school_data["type"] = school_type
    df_school_data["url"] = school["url"]
    if df_school_data.shape[0] > 0:
        return df_school_data
    else:
        return pd.DataFrame()


def get_all_data(schools):

    # Output lists
    df_all = pd.DataFrame()

    # Initialize a multiprocessing pool that will close after finishing execution.
    with Pool(NUM_PROCS) as pool:
        results = pool.map(get_school_data, schools)

    for r in results:
        if r.shape[0] > 0:
            df_all = pd.concat([df_all, r], axis=0)

    return df_all


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


if __name__ == "__main__":
    for lista in chunks(schools, 50):

        df = get_all_data(lista)

        df.to_csv(
            f'data/school_data_{lista[0]["SchulNr"]}_{lista[-1]["SchulNr"]}.csv',
            encoding="utf-8",
        )
        print(f'{lista[0]["SchulNr"]}_{lista[-1]["SchulNr"]} is done')
