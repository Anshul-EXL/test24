#!/usr/bin/env python3
# Streamlit page: Sales Navigator → (optional) ZoomInfo Enrichment (Split Flow)
# Edge logic unchanged (same driver launch as before). Chrome attaches to an existing
# Chrome started with --remote-debugging-port=9222.

import os, ssl, time, json, random, re, unicodedata
from datetime import datetime
from pathlib import Path
from os import getcwd

import numpy as np
import pandas as pd
import requests
import streamlit as st
from typing import Optional

# ===== Streamlit FIRST call =====
st.set_page_config(page_title="EXL — Harvester (SN → ZoomInfo) | Edge (unchanged) + Chrome@9222", page_icon="🧲", layout="wide")

# Optional top-nav
try:
    from exl_ui import render_top_nav, auto_splash_on_first_load
    auto_splash_on_first_load("Loading EXLlead.ai…", min_ms=20)
    render_top_nav(active="EXL Lead.AI — Unified Dashboard")
except Exception:
    st.markdown("### EXL Lead.AI — Unified Dashboard")

# ---------- Selenium ----------
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver

# EDGE (unchanged)
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# CHROME (attach to debug)
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ---------- Optional helpers ----------
try:
    import pyperclip
    HAVE_PYPERCLIP = True
except Exception:
    HAVE_PYPERCLIP = False

# ----------------- Paths / Config -----------------
BASE = Path.cwd()
FILES_DIR = BASE / "Files"
UPLOADS_DIR = BASE / "Uploads"
FILES_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)

SP_FOLDER = st.text_input(
    "SharePoint folder (for logs/credits)",
    value=os.getenv(
        "SP_FOLDER",
        "https://exlservicenam-my.sharepoint.com/personal/prashant195947_exlservice_com/Documents/Desktop/For MDM Application/MDM_additional_files/",
    ),
)
SP_LOG_FILE = "Sn_logsheet.xlsx"
SP_LOG_FILE_ROLL = "Sn_logsheet1.xlsx"

DB_PATH = os.path.abspath(os.getenv("EXL_DB_PATH", "exl_outreach.db"))
st.caption(f"DB: `{DB_PATH}`")

# =========================
# ===== Global state  =====
# =========================
ss = st.session_state
ss.setdefault("driver", None)                # Selenium driver (Edge/Chrome)
ss.setdefault("browser_choice", "Edge")      # "Edge" or "Chrome"
ss.setdefault("chrome_debug_addr", "127.0.0.1:9222")
ss.setdefault("sn_headers", None)
ss.setdefault("sn_cookies", None)
ss.setdefault("sp_cookies", None)
ss.setdefault("sn_messages", [])
ss.setdefault("sn_url_template", "")
ss.setdefault("df_sn", pd.DataFrame())          # Phase 1 result
ss.setdefault("df_enriched", pd.DataFrame())    # Phase 2 result
ss.setdefault("username", "")

def push_msg(m: str):
    ss.sn_messages.append(m)

# =========================
# ===== HTTP Session  =====
# =========================
class TLSAdapter(requests.adapters.HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.set_ciphers("DEFAULT@SECLEVEL=1")
        kwargs["ssl_context"] = ctx
        return super(TLSAdapter, self).init_poolmanager(*args, **kwargs)

SES = requests.session()
SES.mount("https://", TLSAdapter())
REQ_TIMEOUT = (5, 30)

# =========================
# ===== Selenium init  ====
# =========================
# EDGE — KEEPING SAME LOGIC as before (webdriver_manager → EdgeService → webdriver.Edge)
def get_edge_driver() -> RemoteWebDriver:
    driver_path = os.path.join(getcwd(), "drivers", "msedgedriver.exe")
    service = EdgeService(driver_path)
    #binary = webdriver.Edge(service=service)
    opts = EdgeOptions()
    opts.add_argument("start-maximized")
    driver = webdriver.Edge(service=service, options=opts)
    driver.set_window_size(1400, 900)
    return driver

# If your original code used a fixed msedgedriver.exe path, uncomment this and set EDGE_DRIVER_PATH:
# def get_edge_driver() -> RemoteWebDriver:
#     edge_driver_path = os.getenv("EDGE_DRIVER_PATH")  # e.g., r"C:\msdriver\msedgedriver.exe"
#     if not edge_driver_path:
#         raise RuntimeError("Set EDGE_DRIVER_PATH to your msedgedriver.exe")
#     opts = EdgeOptions()
#     opts.add_argument("start-maximized")
#     service = EdgeService(edge_driver_path)
#     driver = webdriver.Edge(service=service, options=opts)
#     driver.set_window_size(1400, 900)
#     return driver

# CHROME — ATTACH to existing Chrome @ debug port (no change to Edge flow)
def get_chrome_driver_attach(debug_addr: str = "127.0.0.1:9222") -> RemoteWebDriver:
    path = ChromeDriverManager().install()
    opts = ChromeOptions()
    opts.add_argument("start-maximized")
    opts.add_argument("--remote-allow-origins=*")
    opts.add_experimental_option("debuggerAddress", debug_addr)
    service = ChromeService(path)
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_window_size(1400, 900)
    return driver

# =========================
# ===== SharePoint auth ===
# =========================
def cookie_sharepoint(driver: RemoteWebDriver, folder_url: str) -> dict:
    driver.get(folder_url)
    time.sleep(random.uniform(5, 10))
    cookies = driver.get_cookies()
    return {c["name"]: c["value"] for c in cookies}

# =========================
# ===== SalesNav auth  ====
# =========================
def cookie_keys(driver: RemoteWebDriver) -> tuple[dict, dict]:
    driver.get("https://www.linkedin.com/login")
    st.info("Please log in to LinkedIn in the opened browser…")
    time.sleep(50)  # MFA cushion
    driver.get("https://www.linkedin.com/sales")
    time.sleep(random.uniform(8, 11))
    cookies = driver.get_cookies()
    cookies_ = {c["name"]: c["value"] for c in cookies}
    headers_ = {
        "csrf-token": cookies_.get("JSESSIONID", "")[1:-1] if "JSESSIONID" in cookies_ else "",
        "user-agent": driver.execute_script("return navigator.userAgent;"),
        "X-RestLi-Protocol-Version": "2.0.0",
    }
    return cookies_, headers_

# =========================
# ===== URL builder  ======
# =========================
def SN_url_agent(companies: list[str], seniority: list[str], regions: list[str], Buycent: list[str], driver: RemoteWebDriver) -> str:
    outside = []
    inside1 = []
    for i in companies:
        i = requests.utils.quote(i)
        inside1.append(f"(text%3A{i}%2CselectionType%3AINCLUDED)")
    company_filter = f"(type%3ACURRENT_COMPANY%2Cvalues%3AList({ '%2C'.join(inside1) }))"
    outside.append(company_filter)

    if seniority:
        sen_dic = {
            "CXO": "(id%3A310%2Ctext%3ACXO%2CselectionType%3AINCLUDED)",
            "Director": "(id%3A220%2Ctext%3ADirector%2CselectionType%3AINCLUDED)",
            "Vice President": "(id%3A300%2Ctext%3AVice%2520President%2CselectionType%3AINCLUDED)",
        }
        inside2 = [sen_dic[k] for k in seniority if k in sen_dic]
        if inside2:
            seniority_filter = f"(type%3ASENIORITY_LEVEL%2Cvalues%3AList({ '%2C'.join(inside2) }))"
            outside.append(seniority_filter)

    if regions:
        reg_dic = {
            "APAC": "(id%3A91000003%2Ctext%3AAPAC%2CselectionType%3AINCLUDED)",
            "EMEA": "(id%3A91000007%2Ctext%3AEMEA%2CselectionType%3AINCLUDED)",
            "United States": "(id%3A103644278%2Ctext%3AUnited%2520States%2CselectionType%3AINCLUDED)",
        }
        inside3 = [reg_dic[j] for j in regions if j in reg_dic]
        if inside3:
            region_filter = f"(type%3AREGION%2Cvalues%3AList({ '%2C'.join(inside3) }))"
            outside.append(region_filter)

    if Buycent:
        inside4 = []
        for l in Buycent:
            l = requests.utils.quote(l)
            inside4.append(f"(text%3A{l}%2CselectionType%3AINCLUDED)")
        Buying_filter = f"(type%3ACURRENT_TITLE%2Cvalues%3AList({ '%2C'.join(inside4) }))"
        outside.append(Buying_filter)

    url_created = f"https://www.linkedin.com/sales/search/people?query=(recentSearchParam%3A(doLogHistory%3Atrue)%2Cfilters%3AList({ '%2C'.join(outside) }))"
    url_created = url_created.replace("&", "%2526")
    driver.get(url_created)
    time.sleep(5)
    try:
        label = driver.find_element(By.XPATH, "//label[contains(., 'Save search')]")
        toggle = driver.find_element(By.ID, label.get_attribute("for"))
        driver.execute_script("arguments[0].click();", toggle)
        time.sleep(2)
    except Exception:
        pass
    return driver.current_url

def url_sales(address_sales: str) -> str:
    base1 = "https://www.linkedin.com/sales-api/salesApiLeadSearch?q=savedSearchId&start={a1}&count=25&savedSearchId={a2}&trackingParam=(sessionId:{a3})&decorationId=com.linkedin.sales.deco.desktop.searchv2.LeadSearchResult-13"
    base2 = "https://www.linkedin.com/sales-api/salesApiLeadSearch?q=searchQuery&{a1}&start={a2}&count=25&trackingParam=(sessionId:{a3})&decorationId=com.linkedin.sales.deco.desktop.searchv2.LeadSearchResult-13"
    base3 = "https://www.linkedin.com/sales-api/salesApiLeadSearch?q=sharedSearchId&start={a1}&count=25&sharedSearchId={a2}&sharerSeatId={a3}&trackingParam=(sessionId:{a4})&decorationId=com.linkedin.sales.deco.desktop.searchv2.LeadSearchResult-13"

    if "&viewAllFilters=true" in address_sales:
        address_sales = address_sales.replace("&viewAllFilters=true", "")

    if "savedSearchId=" in address_sales:
        savedid = address_sales.split("savedSearchId=")[1].split("&")[0]
        sessionid = address_sales.split("sessionId=")[-1]
        return base1.format(a1="{start}", a2=savedid, a3=sessionid)

    if "query" in address_sales:
        search = address_sales.split("?")[1].split("&")[0]
        search = search.replace("%3A", ":").replace("%2C", ",")
        sessionid = address_sales.split("sessionId=")[-1]
        return base2.format(a1=search, a2="{start}", a3=sessionid)

    if "sharedSearchId=" in address_sales:
        sharedSearchID = address_sales.split("%2C")[-1]
        sharerSeatId = address_sales.split("%2C")[0].split("sharedSearchId=")[1]
        seesionId = address_sales.split("sessionId=")[1].split("&")[0]
        return base3.format(a1="{start}", a2=sharedSearchID, a3=sharerSeatId, a4=seesionId)

    return ""

# =========================
# ===== Credits (SP)  =====
# =========================
def credit_limit_sn(num: int, username: str) -> int:
    past = "No"
    limit = 5000
    url = SP_FOLDER.rstrip("/") + "/" + SP_LOG_FILE

    r = SES.get(url, cookies=ss.sp_cookies or {}, timeout=REQ_TIMEOUT)
    if r.status_code != 200:
        push_msg("SharePoint cookie missing/expired — refresh cookie.")
        return -1

    tmp = FILES_DIR / "sn_log_tmp.xlsx"
    tmp.write_bytes(r.content)
    df = pd.read_excel(tmp)[["Username", "credits", "Time", "Past"]]

    now_ = datetime.now()
    now = now_.strftime("%x,%X")

    flag = 0
    if username in df["Username"].tolist():
        df["difference"] = df["Time"].apply(lambda x: (now_ - datetime.strptime(x, "%m/%d/%y,%H:%M:%S")).total_seconds() / 3600)
        df = df[df["difference"] < 25]
        df1 = df[df["Past"] == past]
        if username in df1["Username"].tolist():
            df2 = df1[df1["Username"] == username]
            used = df2["credits"].sum()
            if num > limit - used:
                flag = -1
                push_msg(f"Insufficient credits to extract {num} leads.")
                diff = df2["difference"].tolist()
                cred = df2["credits"].tolist()
                for i in range(len(diff)):
                    push_msg(f"You can extract till {limit - used + sum(cred[:i+1])} leads after {25 - diff[i]:.1f} hours")
        df = df.drop(columns=["difference"], errors="ignore")

    if flag == 0:
        df_new = pd.DataFrame([[username, num, now, past]], columns=["Username", "credits", "Time", "Past"])
        df = pd.concat([df, df_new], ignore_index=True)
        df.to_excel(tmp, index=False)
        SES.put(url, data=tmp.read_bytes(), cookies=ss.sp_cookies or {}, timeout=REQ_TIMEOUT)

        url2 = SP_FOLDER.rstrip("/") + "/" + SP_LOG_FILE_ROLL
        r2 = SES.get(url2, cookies=ss.sp_cookies or {}, timeout=REQ_TIMEOUT)
        if r2.status_code == 200:
            (FILES_DIR / "sn_log2_tmp.xlsx").write_bytes(r2.content)
            df2 = pd.read_excel(FILES_DIR / "sn_log2_tmp.xlsx").iloc[:, 1:]
            df2 = pd.concat([df2, df_new], ignore_index=True)
            df2.to_excel(FILES_DIR / "sn_log2_tmp.xlsx", index=False)
            SES.put(url2, data=(FILES_DIR / "sn_log2_tmp.xlsx").read_bytes(), cookies=ss.sp_cookies or {}, timeout=REQ_TIMEOUT)

    return flag

# =========================
# ===== TeamLinks / BC ====
# =========================
def TeamLinks(lead_company_df: pd.DataFrame, driver: RemoteWebDriver, cookies_: dict, headers_: dict) -> pd.DataFrame:
    if lead_company_df.empty or "Sn_Link" not in lead_company_df.columns:
        return lead_company_df
    sn_links = lead_company_df["Sn_Link"].tolist()
    team_links_sn = []
    for sn in sn_links:
        try:
            profile_id = sn.split("/")[-1].rstrip(",")
        except Exception:
            continue
        n = 0
        y = len(team_links_sn)
        while len(team_links_sn) - y == n:
            url3 = f"https://www.linkedin.com/sales-api/salesApiLeadSearch?q=searchQuery&query=(recentSearchParam:(doLogHistory:true),filters:List((type:TEAMLINK_CONNECTION_OF,values:List((id:{profile_id},selectionType:INCLUDED)))))&start={n}&count=25&trackingParam=(sessionId:9DE7JD1eTDKupqnJFherIg%3D%3D)&decorationId=com.linkedin.sales.deco.desktop.searchv2.LeadSearchResult-13"
            r = SES.get(url3, cookies=cookies_, headers=headers_, timeout=REQ_TIMEOUT)
            try:
                js = r.json()
            except Exception:
                break
            if "elements" not in js:
                break
            for el in js["elements"]:
                name = el.get("fullName", "")
                title = ""
                try:
                    title = el["currentPositions"][0]["title"]
                except Exception:
                    pass
                team_links_sn.append([sn, name, title])
            n += 25

    if not team_links_sn:
        return lead_company_df

    df = pd.DataFrame(team_links_sn, columns=["Sn_Link", "Team Link Intro Name", "Team Link Intro Position"])
    temp = df.groupby("Sn_Link").agg(list).reset_index()
    temp["Team Link"] = temp["Team Link Intro Name"].apply(lambda x: "Yes" if x == x else "")
    keep = ["Sn_Link", "Team Link", "Team Link Intro Name", "Team Link Intro Position"]
    return lead_company_df.merge(temp[keep], on="Sn_Link", how="left")

def Buyingcenters(df_bc: pd.DataFrame) -> pd.DataFrame:
    if df_bc.empty:
        return df_bc
    if "title" in df_bc.columns:
        df_bc = df_bc.rename(columns={"title": "Title"})
    if "Title" not in df_bc.columns:
        push_msg("Missing Title column in leads dataframe.")
        return df_bc

    buy_path = UPLOADS_DIR / "buying.xlsx"
    if not buy_path.exists():
        push_msg("Uploads/buying.xlsx not found. Buying center mapping will be empty.")
        df_bc["Buying center"] = ""
        df_bc["word"] = "NA"
        return df_bc

    def check_type(x, combos):
        try:
            for t in combos:
                if t[2] == "N":
                    if str(t[0]).upper() in str(x).upper():
                        return t[1]
                else:
                    if str(t[0]) in str(x):
                        return t[1]
            return ""
        except Exception:
            return ""

    def check_word(x, combos):
        try:
            for t in combos:
                if t[2] == "N":
                    if str(t[0]).upper() in str(x).upper():
                        return t[0]
                else:
                    if str(t[0]) in str(x):
                        return t[0]
            return "NA"
        except Exception:
            return "NA"

    combos = pd.read_excel(buy_path).values.tolist()
    df_bc["Buying center"] = df_bc["Title"].apply(lambda x: check_type(x, combos))
    df_bc["word"] = df_bc["Title"].apply(lambda x: check_word(x, combos))
    return df_bc

# =========================
# ===== ZoomInfo grab  ====
# =========================
def zoom_enrich(df_in: pd.DataFrame, driver: RemoteWebDriver, max_rows: Optional[int] = None, per_contact_pause: float = 0.8) -> pd.DataFrame:
    if df_in is None or df_in.empty:
        return df_in
    try:
        driver.get("https://app.zoominfo.com/#/apps/search/v2/saved")
    except Exception:
        push_msg("Could not open ZoomInfo. Please log in manually in the opened browser.")
        return df_in

    time.sleep(7)

    rows = df_in[["fullName", "companyName"]].fillna("").values.tolist()
    if max_rows:
        rows = rows[:max_rows]

    output = []
    prog = st.progress(0.0, text="ZoomInfo enrichment in progress…")
    total = max(1, len(rows))

    for idx, (full, comp) in enumerate(rows, start=1):
        inner = [full, comp]
        copied_value = "initial"
        try:
            time.sleep(2)
            btn = driver.find_element(By.XPATH, "//button[contains(@data-automation-id,'contactName_label')]")
            #WebDriverWait(driver, 10).until(
             #   EC.element_to_be_clickable((By.XPATH, "//button[contains(@data-automation-id,'contactName_label')]"))
            #)
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(2)
            #inp = WebDriverWait(driver, 10).until(
            #    EC.presence_of_element_located((By.XPATH, "//input[contains(@data-automation-id,'contactName_input')]"))
            #)
            inp = driver.switch_to.active_element
            time.sleep(2)
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", inp)
            time.sleep(2)
            driver.execute_script("arguments[0].focus();", inp)
            
            inp.clear(); inp.send_keys(full); inp.send_keys(Keys.RETURN);
            time.sleep(3)

            btn2 = driver.find_element(By.XPATH, "//button[contains(@data-automation-id,'companyNameUrlTicker_label')]")
            #WebDriverWait(driver, 10).until(
             #   EC.element_to_be_clickable((By.XPATH, "//button[contains(@data-automation-id,'companyNameUrlTicker_label')]")))
            driver.execute_script("arguments[0].click();", btn2)
            time.sleep(2)
            inp2 = driver.switch_to.active_element
            time.sleep(2)
            driver.execute_script("arguments[0].focus();", inp2)
            inp2.clear(); inp2.send_keys(comp); inp2.send_keys(Keys.RETURN);inp2.send_keys(Keys.ESCAPE);
            time.sleep(2)
        except Exception:
            copied_value = "error"

        try:
            name = driver.find_element(By.XPATH, "//span[@data-automation-id='card-name']").text
        except Exception:
            name = "no name"
        print(name)
        first = full.lower().split(" ")[0]
        last = full.lower().split(" ")[1]
        if ((first in name.lower()) and (last in name.lower())):
            try:
                email_btn = driver.find_element(By.XPATH, "//button[contains(@aria-label,'Copy Business Email')]")
                driver.execute_script("arguments[0].click();", email_btn)
                time.sleep(2)
                if HAVE_PYPERCLIP:
                    copied_value = pyperclip.paste()
                else:
                    copied_value = "install pyperclip to read clipboard"
                time.sleep(2)
            except Exception:
                copied_value = "no email id"
        else:
            copied_value = "not found"
        print(copied_value)

        try:
            clr = WebDriverWait(driver, 4).until(EC.element_to_be_clickable((By.ID, "btn-clear-all")))
            driver.execute_script("arguments[0].click();", clr)
        except Exception:
            pass
        time.sleep(per_contact_pause)

        

        inner.append(copied_value)
        output.append(inner)
        prog.progress(idx / total, text=f"ZoomInfo enrichment… {idx}/{total}")

    prog.empty()
    email_df = pd.DataFrame(output, columns=["fullName", "companyName", "Email"])
    return df_in.merge(email_df, on=["fullName", "companyName"], how="left")

# =========================
# ===== Lead harvest   ====
# =========================
def Lead_details_SN_only(url_template: str, cookies_: dict, headers_: dict, username: str, driver: RemoteWebDriver, include_teamlinks: bool = True, include_buying: bool = True) -> pd.DataFrame:
    list1 = ["fullName", "lastName", "firstName", "geoRegion"]
    list2 = ["companyName", "title", "tenureAtPosition", "tenureAtCompany"]
    list4 = ["numYears", "numMonths"]

    total_leads = []
    n = 0
    total_available = 0

    while n == 0:
        url = url_template.format(start=n)
        r = SES.get(url, cookies=cookies_, headers=headers_, timeout=REQ_TIMEOUT)

        if n == 0:
            try:
                js = r.json()
                total_available = js["paging"]["total"]
            except Exception:
                push_msg("Sales API returned non-JSON. Re-login to Sales Navigator.")
                return pd.DataFrame()

            if total_available > 2400:
                push_msg("Search exceeds 2400 leads. Narrow filters.")
                return pd.DataFrame()

            if credit_limit_sn(total_available, username) != 0:
                return pd.DataFrame()

        if r.status_code != 200:
            push_msg("Sales API error. Re-login to Sales Navigator.")
            return pd.DataFrame()

        js = r.json()
        elements = js.get("elements", [])
        if not elements:
            break

        for lead in elements:
            indv = []
            for k in list1:
                indv.append(lead.get(k, ""))

            try:
                profile_ID = lead["entityUrn"].split("(")[1].split(",")[0]
                indv += [f"https://www.linkedin.com/sales/lead/{profile_ID},", f"https://www.linkedin.com/in/{profile_ID}"]
            except Exception:
                indv += ["", ""]

            for j in range(len(list2)):
                if j < 2:
                    try:
                        indv.append(lead["currentPositions"][0][list2[j]])
                    except Exception:
                        indv.append("")
                else:
                    for k in list4:
                        try:
                            indv.append(lead["currentPositions"][0][list2[j]][k])
                        except Exception:
                            indv.append("")

            try:
                code = lead["currentPositions"][0]["companyUrnResolutionResult"]["entityUrn"].split(":")[-1]
            except Exception:
                code = 0
            indv.append(code)
            total_leads.append(indv)

        n += 25
        if n >= min(total_available, 2400):
            break
        time.sleep(0.3)
        
    total_leads = total_leads[:5]
    push_msg(f"Leads extracted: {len(total_leads)}")

    columns1 = list1 + ["Sn_Link", "Linkedin ID URL"] + list2[:2] + \
               ["yearsinposition", "monthsinposition", "yearsincompany", "monthsincompany", "code"]
    df = pd.DataFrame(total_leads, columns=columns1)

    if include_teamlinks:
        df = TeamLinks(df, driver, cookies_, headers_)
    if include_buying:
        df = Buyingcenters(df)

    return df

# =========================
# ===== Save / DB I/O  ====
# =========================
import sqlite3

def ensure_table(conn: sqlite3.Connection):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS sn_zoom_leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        user TEXT,
        campaign_name TEXT,
        fullName TEXT,
        firstName TEXT,
        lastName TEXT,
        geoRegion TEXT,
        Sn_Link TEXT,
        Linkedin_ID_URL TEXT,
        companyName TEXT,
        Title TEXT,
        yearsinposition INTEGER,
        monthsinposition INTEGER,
        yearsincompany INTEGER,
        monthsincompany INTEGER,
        code TEXT,
        Team_Link TEXT,
        Team_Link_Intro_Name TEXT,
        Team_Link_Intro_Position TEXT,
        Buying_center TEXT,
        word TEXT,
        Email TEXT
    )
    """)
    conn.commit()

def save_df_to_db(df: pd.DataFrame, campaign_name: str, user: str) -> int:
    if df is None or df.empty:
        return 0
    out = pd.DataFrame()
    out["created_at"] = datetime.utcnow().isoformat()
    out["user"] = user or ""
    out["campaign_name"] = campaign_name or ""

    def getc(col, default=""):
        return df[col] if col in df.columns else default

    out["fullName"] = getc("fullName")
    out["firstName"] = getc("firstName")
    out["lastName"] = getc("lastName")
    out["geoRegion"] = getc("geoRegion")
    out["Sn_Link"] = getc("Sn_Link")
    out["Linkedin_ID_URL"] = getc("Linkedin ID URL")
    out["companyName"] = getc("companyName")
    out["Title"] = getc("title") if "title" in df.columns else getc("Title")
    out["yearsinposition"] = getc("yearsinposition", 0)
    out["monthsinposition"] = getc("monthsinposition", 0)
    out["yearsincompany"] = getc("yearsincompany", 0)
    out["monthsincompany"] = getc("monthsincompany", 0)
    out["code"] = getc("code")
    out["Team_Link"] = getc("Team Link")

    def _as_str(x):
        if isinstance(x, list):
            return ", ".join([str(i) for i in x][:10])
        return "" if (pd.isna(x) or x is None) else str(x)

    out["Team_Link_Intro_Name"] = getc("Team Link Intro Name").apply(_as_str) if "Team Link Intro Name" in df.columns else ""
    out["Team_Link_Intro_Position"] = getc("Team Link Intro Position").apply(_as_str) if "Team Link Intro Position" in df.columns else ""
    out["Buying_center"] = getc("Buying center")
    out["word"] = getc("word")
    out["Email"] = getc("Email") if "Email" in df.columns else ""

    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        ensure_table(conn)
        out.to_sql("sn_zoom_leads", conn, if_exists="append", index=False)
        conn.commit()
    return len(out)

def upsert_emails_in_db(df_with_emails: pd.DataFrame, campaign_name: str, user: str) -> int:
    if df_with_emails is None or df_with_emails.empty or "Email" not in df_with_emails.columns:
        return 0
    updated = 0
    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        ensure_table(conn)
        cur = conn.cursor()
        for _, r in df_with_emails.iterrows():
            full = str(r.get("fullName", "") or "")
            comp = str(r.get("companyName", "") or "")
            email = str(r.get("Email", "") or "")
            if not (full or comp or email):
                continue
            cur.execute("""
                UPDATE sn_zoom_leads
                   SET Email = ?
                 WHERE user = ? AND campaign_name = ?
                   AND fullName = ? AND companyName = ?
            """, (email, user or "", campaign_name or "", full, comp))
            if cur.rowcount == 0:
                cur.execute("""
                    INSERT INTO sn_zoom_leads (created_at, user, campaign_name, fullName, companyName, Email)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (datetime.utcnow().isoformat(), user or "", campaign_name or "", full, comp, email))
            updated += 1
        conn.commit()
    return updated

def fetch_count_from_db(user: str, campaign_name: str) -> int:
    user = user or ""
    campaign_name = campaign_name or ""
    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        ensure_table(conn)
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM sn_zoom_leads WHERE user=? AND campaign_name=?",
            (user, campaign_name),
        )
        row = cur.fetchone()
        return int(row[0]) if row and row[0] is not None else 0

def fetch_from_db(user: str, campaign_name: str, limit: int = 200) -> pd.DataFrame:
    user = user or ""
    campaign_name = campaign_name or ""
    limit = max(1, int(limit))
    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        ensure_table(conn)
        q = f"""
        SELECT
            id, created_at, user, campaign_name,
            fullName, companyName, Title, Email,
            Linkedin_ID_URL, Sn_Link, geoRegion, Buying_center, word
        FROM sn_zoom_leads
        WHERE user = ? AND campaign_name = ?
        ORDER BY id DESC
        LIMIT {limit}
        """
        return pd.read_sql_query(q, conn, params=(user, campaign_name))

# =========================
# ===== UI — Controls  ====
# =========================
with st.sidebar:
    st.subheader("Browser & Auth")
    ss.browser_choice = st.radio("Browser", ["Edge (unchanged)", "Chrome (attach @9222)"], index=0, horizontal=False)

    if "Chrome" in ss.browser_choice:
        st.text_input("Debugger address (host:port)", key="chrome_debug_addr", value=ss.chrome_debug_addr)
        with st.expander("How to start Chrome in debug mode"):
            st.markdown("**Windows**")
            st.code(r'''"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir=%LOCALAPPDATA%\Google\Chrome\User Data\Debug9222''')
            st.markdown("**macOS**")
            st.code(r"""/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-dev""")

    colA, colB = st.columns(2)
    with colA:
        if st.button("Launch / Attach"):
            try:
                if ss.driver:
                    try: ss.driver.quit()
                    except Exception: pass

                if "Edge" in ss.browser_choice:
                    # EDGE: same logic as before
                    ss.driver = get_edge_driver()
                    st.success("Edge started (unchanged logic).")
                else:
                    # CHROME: attach-only to existing Chrome debug port
                    ss.driver = get_chrome_driver_attach(ss.chrome_debug_addr or "127.0.0.1:9222")
                    st.success(f"Attached to Chrome at {ss.chrome_debug_addr}.")

            except Exception as e:
                st.error(f"Driver error: {e}")
    with colB:
        if st.button("Close Browser"):
            try:
                if ss.driver:
                    ss.driver.quit()
                    ss.driver = None
                    st.success("Closed.")
            except Exception:
                pass

    st.text_input("Username (for credits log)", key="username", value=ss.get("username",""))

    if st.button("Get SharePoint cookie"):
        if not ss.driver:
            st.error("Open a browser first.")
        else:
            try:
                ss.sp_cookies = cookie_sharepoint(ss.driver, SP_FOLDER)
                st.success("SharePoint cookie captured.")
            except Exception as e:
                st.error(f"SP cookie fail: {e}")

    if st.button("Capture SN cookies/headers"):
        if not ss.driver:
            st.error("Open a browser first.")
        else:
            try:
                c, h = cookie_keys(ss.driver)
                ss.sn_cookies = c
                ss.sn_headers = h
                st.success("Sales Navigator cookies/headers captured.")
            except Exception as e:
                st.error(f"SN auth fail: {e}")

    st.divider()
    if st.button("Reset Page State"):
        keys = ["sn_headers","sn_cookies","sp_cookies","sn_messages","sn_url_template","df_sn","df_enriched"]
        for k in keys:
            ss[k] = [] if k=="sn_messages" else (pd.DataFrame() if "df_" in k else None)
        st.success("State cleared. Re-run the page if needed.")

st.title("Lead.AI — Data Harvester (Split)")

# -------- Phase 1: Build + Harvest SN (no ZoomInfo) --------
st.markdown("## Phase 1 — Sales Navigator (fetch, save & export)")

with st.form("sn_builder"):
    col1, col2, col3 = st.columns(3)
    with col1:
        companies_raw = st.text_area("Companies (one per line)", height=120, placeholder="Acme Inc\nGlobex\nUmbrella")
        seniority = st.multiselect("Seniority", ["CXO", "Director", "Vice President"])
    with col2:
        regions = st.multiselect("Regions", ["APAC", "EMEA", "United States"])
        buying = st.multiselect(
            "Buying Centers (groups)",
            ["IT/ Technology/Data Management/ Gen AI", "Marketing", "Customer support & service/CX", "F&A", "Procurement"],
        )
    with col3:
        campaign_name = st.text_input("Campaign/Label (for DB rows)", value="SN Harvest")
        file_name_sn = st.text_input("Excel filename (no ext.)", value=f"sn_{datetime.now().strftime('%Y%m%d_%H%M')}")
        include_teamlinks = st.checkbox("Include TeamLinks (slower)", value=True)
        include_buying = st.checkbox("Include Buying center mapping", value=True)

    run_build = st.form_submit_button("1) Build SN URL & Save Search")

if run_build:
    if not ss.driver:
        st.error("Open a browser first.")
    else:
        companies = [c.strip() for c in (companies_raw or "").splitlines() if c.strip()]
        bc_map = {
            "IT/ Technology/Data Management/ Gen AI": ["Data", "AI", "ML", "Business Intelligence", "Artificial Intelligence", "Machine learning", "Data Architecture", "Data Engineering", "Data Governance", "Data Management", "Innovation", "R&D"],
            "Marketing": ["Marketing", "Commercial", "Consumer & Market Insights", "Customer Analytics", "Pricing & Promotions", "Trade Marketing Analytics", "Omnichannel Strategy", "Retail Media Analytics", "Sales Operations", "E-commerce & Online Marketplaces", "Last-Mile Delivery Operations"],
            "Customer support & service/CX": ["Aftersales", "Customer Support", "Customer experience", "Contact Centre", "Call Centre", "Omnichannel Customer Experience", "Customer Experience & Loyalty Programs", "Personalization"],
            "F&A": ["Sales & Demand Planning", "Revenue Growth Management", "Financial Process Efficiency", "Audit", "F&A", "FP&A", "Account Receivable", "Account payable", "Order to Cash", "Procure to pay", "Controller", "Shared Services"],
            "Procurement": ["Procurement", "Vendor", "Workforce"],
        }
        Buycent = []
        for bc in buying:
            Buycent += bc_map.get(bc, [])

        try:
            url_built = SN_url_agent(companies, seniority, regions, Buycent, ss.driver)
            st.success("SN page opened & saved-search toggled.")
            ss.sn_url_template = url_sales(url_built)
            st.code(ss.sn_url_template or "(failed to derive API template)")
        except Exception as e:
            st.error(f"Could not build SN URL: {e}")

c1, c2, c3 = st.columns(3)
with c1:
    if st.button("2) Harvest from Sales API (SN only)"):
        if not (ss.sn_url_template and ss.sn_cookies and ss.sn_headers):
            st.error("Missing API template or SN auth. Capture cookies/headers and build URL first.")
        elif not ss.username:
            st.error("Enter Username (for SharePoint credits).")
        else:
            with st.spinner("Harvesting from Sales API…"):
                df = Lead_details_SN_only(
                    ss.sn_url_template,
                    ss.sn_cookies,
                    ss.sn_headers,
                    ss.username,
                    ss.driver,
                    include_teamlinks=include_teamlinks,
                    include_buying=include_buying,
                )
                ss.df_sn = df
                if df is None or df.empty:
                    st.error("No leads found or blocked by credits.")
                else:
                    st.success(f"Leads harvested: {len(df)} (SN only)")

with c2:
    if st.button("3) Save SN-only rows to DB"):
        df = ss.df_sn
        if df is None or df.empty:
            st.error("No data to save. Harvest first.")
        else:
            n = save_df_to_db(df, campaign_name, ss.username)
            total = fetch_count_from_db(ss.username, campaign_name)
            st.success(f"Saved {n} SN rows into `sn_zoom_leads`.")
            st.caption(f"DB now has **{total} rows** for campaign: **{campaign_name}**")
            st.markdown("##### DB Snapshot (latest)")
            st.dataframe(fetch_from_db(ss.username, campaign_name, 200), use_container_width=True)

with c3:
    if st.button("4) Download SN-only Excel"):
        df = ss.df_sn
        if df is None or df.empty:
            st.error("No data to export. Harvest first.")
        else:
            out = FILES_DIR / f"{file_name_sn}.xlsx"
            df.to_excel(out, index=False)
            st.success(f"Saved: {out}")
            with open(out, "rb") as f:
                st.download_button("Download file", f, file_name=out.name, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.markdown("#### Preview — SN (Phase 1)")
if not ss.df_sn.empty:
    st.dataframe(ss.df_sn.head(200), use_container_width=True)

st.divider()

# -------- Phase 2: ZoomInfo enrichment (optional) --------
st.markdown("## Phase 2 — ZoomInfo (optional enrichment)")

with st.container():
    colz1, colz2, colz3, colz4 = st.columns([1,1,1,1])
    with colz1:
        if st.button("Open ZoomInfo (login)"):
            if not ss.driver:
                st.error("Open a browser first.")
            else:
                try:
                    ss.driver.get("https://login.zoominfo.com/")
                    st.info("Log in to ZoomInfo in the opened browser.")
                except Exception as e:
                    st.error(f"ZoomInfo open failed: {e}")
    with colz2:
        max_rows = st.number_input("Max rows to enrich (0 = all)", min_value=0, value=0, step=50)
    with colz3:
        per_pause = st.slider("Pause per contact (sec)", min_value=0.2, max_value=2.0, value=0.8, step=0.1)
    with colz4:
        limit_rows = None if max_rows == 0 else int(max_rows)

    if st.button("5) Run ZoomInfo enrichment on current SN results"):
        df = ss.df_sn
        if df is None or df.empty:
            st.error("No SN data available. Run Phase 1 first.")
        elif not ss.driver:
            st.error("Open a browser and ensure ZoomInfo is logged in.")
        else:
            with st.spinner("Enriching with ZoomInfo…"):
                enriched = zoom_enrich(df.copy(), ss.driver, max_rows=limit_rows, per_contact_pause=per_pause)
                ss.df_enriched = enriched
                st.success("ZoomInfo enrichment done (emails merged into dataframe).")

colze1, colze2 = st.columns(2)
with colze1:
    if st.button("6) Save ENRICHED rows to DB (upsert emails)"):
        df = ss.df_enriched if not ss.df_enriched.empty else ss.df_sn
        if df is None or df.empty:
            st.error("Nothing to save. Run enrichment or SN first.")
        else:
            if "Email" in df.columns and df["Email"].notna().any():
                n = upsert_emails_in_db(df, campaign_name, ss.username)
                action = "Upserted Email into"
            else:
                n = save_df_to_db(df, campaign_name, ss.username)
                action = "Saved"
            total = fetch_count_from_db(ss.username, campaign_name)
            st.success(f"{action} {n} rows for campaign '{campaign_name}'.")
            st.caption(f"DB now has **{total} rows** for campaign: **{campaign_name}**")
            st.markdown("##### DB Snapshot (latest)")
            st.dataframe(fetch_from_db(ss.username, campaign_name, 200), use_container_width=True)

with colze2:
    if st.button("7) Download ENRICHED Excel"):
        df = ss.df_enriched if not ss.df_enriched.empty else ss.df_sn
        if df is None or df.empty:
            st.error("No data to export.")
        else:
            out = FILES_DIR / f"{file_name_sn}_enriched.xlsx"
            df.to_excel(out, index=False)
            st.success(f"Saved: {out}")
            with open(out, "rb") as f:
                st.download_button("Download enriched file", f, file_name=out.name, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.divider()
st.markdown("#### Preview — Enriched (Phase 2)")
if not ss.df_enriched.empty:
    st.dataframe(ss.df_enriched.head(200), use_container_width=True)

st.divider()
st.markdown("#### Messages / Log")
for m in ss.sn_messages:
    st.write("•", m)
