#!/usr/bin/python3
import requests
from requests import Request, Session
from requests_html import HTMLSession
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from datetime import datetime, date
import hashlib
import pandas as pd
import numpy as np
import re
import logging
import argparse
import time
import threading
import json

from bigcharts_md import bc_quote

# logging setup
logging.basicConfig(level=logging.INFO)

#####################################################

class yfnews_reader:
    """
    Read Yahoo Finance news reader, Word Vectorizer, Positive/Negative sentiment analyzer
    """

    # global accessors
    symbol = ""             # Unique company symbol
    yfqnews_url = ""        # the URL that is being worked on
    js_session = ""         # main requests session
    js_resp0 = ""           # HTML session get() - response handle
    js_resp2 = ""           # JAVAScript session get() - response handle
    yfn_all_data =""        # JSON dataset contains ALL data
    yfn_htmldata = ""       # Page in HTML
    yfn_jsdata = ""         # Page in JavaScript-HTML
    ml_brief = []           # ML TXT matrix for Naieve Bayes Classifier pre Count Vectorizer
    ul_tag_dataset = ""     # BS4 handle of the <tr> extracted data
    yfn_df0 = ""            # DataFrame 1
    yfn_df1 = ""            # DataFrame 2
    inst_uid = 0
    yti = 0                 # Unique instance identifier
    cycle = 0               # class thread loop counter
    soup = ""               # BS4 shared handle between UP & DOWN (1 URL, 2 embeded data sets in HTML doc)
    args = []               # class dict to hold global args being passed in from main() methods

                            # yahoo.com header/cookie hack
    yahoo_headers = { \
                    'authority': 'yahoo.com', \
                    'path': '/v1/finance/trending/US?lang=en-US&region=US&count=5&corsDomain=finance.yahoo.com', \
                    'origin': 'https://finance.yahoo.com', \
                    'referer': 'https://finance.yahoo.com/', \
                    'sec-ch-ua': '"Chromium";v="92", " Not A;Brand";v="99", "Google Chrome";v="92"', \
                    'sec-ch-ua-mobile': '"?0"', \
                    'sec-fetch-mode': 'cors', \
                    'sec-fetch-site': 'cross-site', \
                    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36' }


    def __init__(self, yti, symbol, global_args):
        cmi_debug = __name__+"::"+self.__init__.__name__
        logging.info('%s - INIT' % cmi_debug )
        # init empty DataFrame with preset colum names
        self.args = global_args
        self.symbol = symbol
        self.yti = yti
        self.js_session = HTMLSession()                        # init JAVAScript processor early
        self.js_session.cookies.update(self.yahoo_headers)     # load cookie/header hack data set into session
        #self.up_df0 = pd.DataFrame(columns=[ 'Row', 'Symbol', 'Co_name', 'Cur_price', 'Prc_change', 'Pct_change', "Vol", 'Vol_pct', 'Time' ] )
        #self.down_df1 = pd.DataFrame(columns=[ 'Row', 'Symbol', 'Co_name', 'Cur_price', 'Prc_change', 'Pct_change', "Vol", 'Vol_pct', 'Time' ] )
        #self.df2 = pd.DataFrame(columns=[ 'ERank', 'Symbol', 'Co_name', 'Cur_price', 'Prc_change', 'Pct_change', "Vol", 'Vol_pct', 'Time' ] )
        return

# method #1
    def yfn_bintro(self):
        """
        DELETE ME - redundent
        Initial blind intro to yahoo.com/news JAVASCRIPT page
        NOTE: BeautifulSoup scraping required as no REST API endpoint is available.
              Javascript engine processing may be required to process/read rich meida JS page data
        """

        cmi_debug = __name__+"::"+self.yfn_bintro.__name__+".#"+str(self.yti)
        logging.info('%s - IN' % cmi_debug )

        # Initial blind get - present ourself to yahoo.com so we can extract critical cookies
        logging.info('%s - blind intro get()' % cmi_debug )
        self.js_session.cookies.update(self.yahoo_headers)    # redundent as it's done in INIT but I'm not sure its persisting from there
        with self.js_session.get("https://www.finance.yahoo.com", stream=True, headers=self.yahoo_headers, cookies=self.yahoo_headers, timeout=5 ) as self.js_resp0:
            logging.info('%s - EXTRACT/INSERT 8 special cookies  ' % cmi_debug )
            self.js_session.cookies.update({'B': self.js_resp0.cookies['B']} )    # yahoo cookie hack

        # 2nd get with the secret yahoo.com cookies now inserted
        # NOTE: Just the finaince.Yahoo.com MAIN landing page - generic news
        logging.info('%s - rest API read json' % cmi_debug )
        with self.js_session.get("https://www.finance.yahoo.com", stream=True, headers=self.yahoo_headers, cookies=self.yahoo_headers, timeout=5 ) as self.js_resp2:
            # read the webpage with our Javascript engine processor
            logging.info('%s - Javascript engine processing disabled...' % cmi_debug )
            #self.js_resp2.html.render()    # render JS page
            logging.info('%s - Javascript engine completed!' % cmi_debug )

            # Setup some initial data structures via an authenticated/valid connection
            logging.info('%s - store FULL json dataset' % cmi_debug )
            # self.uvol_all_data = json.loads(self.js_resp2.text)
            logging.info('%s - store data 1' % cmi_debug )

        # Xray DEBUG
        if self.args['bool_xray'] is True:
            print ( f"=========================== {self.yti} / session cookies ===========================" )
            for i in self.js_session.cookies.items():
                print ( f"{i}" )

        return

# method 2
    def update_headers(self, symbol):
        cmi_debug = __name__+"::"+self.update_headers.__name__+".#"+str(self.yti)
        logging.info('%s - IN' % cmi_debug )

        self.symbol = symbol
        logging.info('%s - set cookies/headers path: object' % cmi_debug )
        self.path = '/quote/' + self.symbol + '/news?p=' + self.symbol
        self.js_session.cookies.update({'path': self.path} )
        logging.info('finance.yahoo::update_headers.## - cookies/headers path: object: %s' % self.path )

        if self.args['bool_xray'] is True:
            print ( f"=========================== {self.yti} / session cookies ===========================" )
            for i in self.js_session.cookies.items():
                print ( f"{i}" )

        return

# method 3
    def update_cookies(self):
        # assumes that the requests session has already been established
        cmi_debug = __name__+"::"+self.update_cookies.__name__+".#"+str(self.yti)
        logging.info('%s - REDO the cookie extract & update  ' % cmi_debug )
        self.js_session.cookies.update({'B': self.js_resp0.cookies['B']} )    # yahoo cookie hack
        return

# method 4
    def form_url_endpoint(self, symbol):
        """
        This is the explicit NEWS URL that is used for the request get()
        NOTE: assumes that path header/cookie has been set first
        #
        URL endpoints available (examples)
        All related news        - https://finance.yahoo.com/quote/IBM/?p=IBM
        Symbol specific news    - https://finance.yahoo.com/quote/IBM/news?p=IBM
        Symbol press releases   - https://finance.yahoo.com/quote/IBM/press-releases?p=IBM
        Symbol research reports - https://finance.yahoo.com/quote/IBM/reports?p=IBM
        """

        cmi_debug = __name__+"::"+self.form_url_endpoint.__name__+".#"+str(self.yti)
        logging.info( f'%s - form URL endpoint for: {symbol}' % cmi_debug )
        self.yfqnews_url = 'https://finance.yahoo.com' + self.path    # use global accessor (so all paths are consistent)
        logging.info('finance.yahoo.com::form_api_endpoint.## - API endpoint URL: %s' % self.yfqnews_url )
        self.yfqnews_url = self.yfqnews_url
        return

# method 5
    def init_dummy_session(self):
        cmi_debug = __name__+"::"+self.init_dummy_session.__name__+".#"+str(self.yti)
        """
        NOTE: we ping finance.yahoo.com
              No need for a API specific url, as this should be the FIRST get for this url. Goal is to find & extract secret cookies
        Overwrites js_resp0 - initial session handle, *NOT* the main data session handle (js_resp2)
        """

        with self.js_session.get('https://www.finance.yahoo.com', stream=True, headers=self.yahoo_headers, cookies=self.yahoo_headers, timeout=5 ) as self.js_resp0:
            logging.info('%s - extract & update GOOD cookie  ' % cmi_debug )
            # self.js_session.cookies.update({'B': self.js_resp0.cookies['B']} )    # yahoo cookie hack
            # if the get() succeds, the response handle is automatically saved in Class Global accessor -> self.js_resp0
        return

# method 6
    def do_simple_get(self):
        """
        get simple raw HTML data structure (data not processed by JAVAScript engine)
        NOTE: get URL is assumed to have allready been set (self.yfqnews_url)
              Assumes cookies have already been set up. NO cookie update done here
        """
        cmi_debug = __name__+"::"+self.do_simple_get.__name__+".#"+str(self.yti)
        logging.info( f'%s - Simple HTML request get() on URL: {self.yfqnews_url}' % cmi_debug )
        with self.js_session.get(self.yfqnews_url, stream=True, headers=self.yahoo_headers, cookies=self.yahoo_headers, timeout=5 ) as self.js_resp0:
            logging.info('%s - Simple HTML Request get() completed!- store HTML response dataset' % cmi_debug )
            self.yfn_htmldata = self.js_resp0.text
            # On success, HTML response is saved in Class Global accessor -> self.js_resp0
            # TODO: should do some get() failure testing here

        # Xray DEBUG
        if self.args['bool_xray'] is True:
            print ( f"========================== {self.yti} / HTML get() session cookies ================================" )
            for i in self.js_session.cookies.items():
                print ( f"{i}" )
            print ( f"========================== {self.yti} / HTML get() session cookies ================================" )

        return

# method 7
    def do_js_get(self):
        """
        get JAVAScript engine processed data structure
        NOTE: get URL is assumed to have allready been set (self.yfqnews_url)
              Assumes cookies have already been set up. NO cookie update done here
        """
        cmi_debug = __name__+"::"+self.do_js_get.__name__+".#"+str(self.yti)
        logging.info('%s - IN' % cmi_debug )
        with self.js_session.get(self.yfqnews_url, stream=True, headers=self.yahoo_headers, cookies=self.yahoo_headers, timeout=5 ) as self.js_resp2:
            logging.info('%s - Javascript engine processing...' % cmi_debug )
            # on scussess, raw HTML (non-JS) response is saved in Class Global accessor -> self.js_resp2
            self.js_resp2.html.render()
            # TODO: should do some get() failure testing here
            logging.info('%s - Javascript engine completed! - store JS response dataset' % cmi_debug )
            self.yfn_jsdata = self.js_resp2.text    # store Full JAVAScript dataset handle

        # Xray DEBUG
        if self.args['bool_xray'] is True:
            print ( f"========================== {self.yti} / JS get() session cookies ================================" )
            for i in self.js_session.cookies.items():
                print ( f"{i}" )
            print ( f"========================== {self.yti} / JS get() session cookies ================================" )

        return

# session data extraction methods ##############################################
# method #8
    def scan_news_depth_0(self, symbol, depth, scan_type):
        """
        Evaluates the news items found. Prints stats, but doesnt create any usable structs
        TODO: add args - DEPTH (0, 1, 2) as opposed to multiple depth level methods
              add args - symbol
              add arge - 0 = HTML processor logic / 1 = JavaScript processor logic
        Assumes connect setup/cookies/headers have all been previously setup
        Read & process the raw news HTML data tables from a complex rich meida (highlevel) news parent webpage for an individual stock [Stock:News ].
        Does not extract any news atricles, items or data fields. Just sets up the element extraction zone.
        Returns a BS4 onbject handle pointing to correct news section for deep element extraction.
        """
        cmi_debug = __name__+"::"+self.scan_news_depth_0.__name__+".#"+str(self.yti)
        logging.info('%s - IN' % cmi_debug )
        symbol = symbol.upper()
        depth = int(depth)
        logging.info( f'%s - Scan news for: {symbol} / {self.yfqnews_url}' % cmi_debug )
        if scan_type == 0:    # Simple HTML BS4 scraper
            logging.info( '%s - Read HTML/json data using pre-init session: resp0' % cmi_debug )
            self.soup = BeautifulSoup(self.yfn_htmldata, "html.parser")
            self.ul_tag_dataset = self.soup.find(attrs={"class": "My(0) P(0) Wow(bw) Ov(h)"} )    # produces : list iterator
            # Depth 0 element zones
            #li class = where the data is hiding
            li_superclass_all = self.ul_tag_dataset.find_all(attrs={"class": "js-stream-content Pos(r)"} )
            li_superclass_one = self.ul_tag_dataset.find(attrs={"class": "js-stream-content Pos(r)"} )
            li_subset_all = self.ul_tag_dataset.find_all('li')
            li_subset_one = self.ul_tag_dataset.find('li')
            mini_headline_all = self.ul_tag_dataset.div.find_all(attrs={'class': 'C(#959595)'})
            mini_headline_one = self.ul_tag_dataset.div.find(attrs={'class': 'C(#959595)'})
        else:
            logging.info( '%s - Read JavaScript/json data using pre-init session: resp2' % cmi_debug )
            self.js_resp2.html.render()    # WARN: Assumes sucessfull JavaScript get was previously issued
            self.soup = BeautifulSoup(self.yfn_jsdata, "html.parser")
            logging.info('%s - save JavaScript-engine/json BS4 data handle' % cmi_debug )
            self.ul_tag_dataset = self.soup.find(attrs={"class": "My(0) P(0) Wow(bw) Ov(h)"} )    # TODO: might be diff for JS engine output

        logging.info( f'%s - Found: datasets: {len(self.ul_tag_dataset)}' % cmi_debug )
        logging.info( f'%s - dataset.children: {len(list(self.ul_tag_dataset.children))} / childrens.descendants: {len(list(self.ul_tag_dataset.descendants))}' % cmi_debug )

        # >>Xray DEBUG on<<
        if self.args['bool_xray'] is True:
            print ( f" " )
            x = y = 1
            print ( f"==================== Ins: {self.yti} / tag.children : {x} =========================" )
            for child in self.ul_tag_dataset.children:
                print ( f"{y}: {child.name}" )
                y += 1
                for element in child.descendants:
                    print ( f"{y}: {element.name} ", end="" )
                    y += 1
                print ( f"\n==================== End : {x} =========================" )
                x += 1
        # >>Xray DEBUG off<<

        return

# method #9
    def read_allnews_depth_0(self):
        """
        NOTE: assumes connection was previously setup
              uses default JS session/request handles
              This is main logic loop because we're at the TOP-level news page for this stock
        1. cycle though the top-level NEWS page for this stock
        2. prepare a list of ALL of the articles
        3. For each article, extract some KEY high-level news elements (i.e. Headline, Brief, URL to real article
        4. Wrangle, clean/convert/format the data correctly
        """

        # Data & Elements extrated and computed
        # 1. article url path
        # 2. Is news article url local (on Yahoo.com) or remotely hosted
        # 3. Unique Sha256 Hash of URL
        # 4. Brief (short article headline)
        cmi_debug = __name__+"::"+self.read_allnews_depth_0.__name__+".#"+str(self.yti)
        logging.info('%s - IN' % cmi_debug )
        time_now = time.strftime("%H:%M:%S", time.localtime() )
        x = 0    # num of new articiels read counter

        # Decoded element zones from page dataset (WARN: could change at any time)
        # News : <div class="Py(14px) Pos(r)" data-test-locator="mega" data-reactid="5">
        # Add  : <div class="controller gemini-ad native-ad-item Feedback Pos(r)" data-test-locator="react-gemini-feedback-container" data-beacon="" data-tp-beacon="" data-reactid="24">

        li_superclass_all = self.ul_tag_dataset.find_all(attrs={"class": "js-stream-content Pos(r)"} )
        mini_headline_all = self.ul_tag_dataset.div.find_all(attrs={'class': 'C(#959595)'})
        li_subset_all = self.ul_tag_dataset.find_all('li')
        # class="C(#959595) Fz(11px) D(ib) Mb(6px)
        #micro_headline = self.soup.find_all("i") #attrs={'class': 'Mx(4px)'})

        mtd_0 = li_subset_all    # self.ul_tag_dataset.find_all('li')
        #mtd_1 = self.ul_tag_dataset[1].find_all('li')
        #mtd_2 = self.ul_tag_dataset[2].find_all('li')

        # TODO: possible better implimentation
        #       for child in self.ul_tag_dataset.children:
        r_url = l_url = 0
        ml_ingest = {}
        for datarow in range(len(mtd_0)):
            html_element = mtd_0[datarow]
            x += 1
            print ( f"====== News item: #{x} ===============" )     # DEBUG
            print ( f"News outlet: {html_element.div.find(attrs={'class': 'C(#959595)'}).string }" )     # DEBUG
            data_parent = str( "{:.15}".format(html_element.div.find(attrs={'class': 'C(#959595)'}).string) )
            #shorten down the above data element for the pandas DataFrame insert that happens later...

            # FRUSTRATING element that cant be locally extracted from High-level page
            # TODO: Figure out WHY? - getting this from main page would increase speed by 10x

            # Identify Local or Remote news article
            # An href that begins with http:// is link to external news outlet, otherwise it found a local Rescource Path /..../..../
            rhl_url = False     # safety pre-set
            url_p = urlparse(html_element.a.get('href'))
            if url_p.scheme == "https" or url_p.scheme == "http":    # check URL scheme specifier
                print ( f"Remote news URL: {url_p.netloc}  - Artcile path: {url_p.path}" )     # DEBUG
                data_outlet = url_p.netloc
                data_path = url_p.path
                rhl_url = True    # This URL is remote
                r_url += 1        # count remote URLs
            else:
                print ( f"Local news URL:  finance.yahoo.com  - Article path: {html_element.a.get('href')}" )     # DEBUG
                l_url += 1        # count local URLs
                data_outlet = 'finance.yahoo.com'
                data_path = html_element.a.get('href')

            # Short brief headline...
            print ( f"News headline: {html_element.a.text}" )
            print ( "Intro teaser #: {} {:.400}".format(x, html_element.p.text) )    # truncate long Brief down to 400 chars
            self.ml_brief.append(html_element.p.text)       # add Brief TXT into ML pre count vectorizer matrix

            # URL unique hash
            url_prehash = html_element.a.get('href')        # generate unuque hash for each URL. For dupe tests & comparrisons etc
            result = hashlib.sha256(url_prehash.encode())
            data_urlhash = result.hexdigest()
            print ( f"Hash encoded URL: {result.hexdigest()}" )     # DEBUG

            # BIG logic decision here...!!!
            if self.args['bool_deep'] is True:        # go DEEP & process each news article deeply?
                if rhl_url == False:                  # yahoo,com local? or remote hosted non-yahoo.com article?
                    a_deep_link = 'https://finance.yahoo.com' + url_prehash
                    #
                    deep_data = self.extract_article_data(a_deep_link)      # extract extra data from news article. Returned as list []
                    #
                    ml_inlist = [data_parent, data_outlet, url_prehash, deep_data[0], deep_data[3] ]
                    ml_ingest[x] = ml_inlist        # add this data set to dict{}
                    print ( "\r{} processed...".format(x), end='', flush=True )
                    logging.info('%s - DEEP news article extratcion of 1 article...' % cmi_debug )
                else:
                    logging.info('%s - REMOTE Hard-linked URL - NOT Extracting NEWS from article...' % cmi_debug )
            else:
                logging.info('%s - Not DEEP processing NEWS articles' % cmi_debug )

        print ( " " )
        print ( f"Top level news articles evaluated: {x}")
        print ( f"Local URLs: {l_url} / Remote URLs: {r_url}" )
        print ( " " )
        return ml_ingest        # returns a dict{} ready for ML pre-processing

    # print ( f"== {erow}: == URL.div element: {a_subset[erow].name}" )
    # print ( f" / Date: {a_subset[erow].time.text}" )         # Pretty data
    # print ( f"== {erow}: == URL.div element: {a_subset[erow]}" )

# method 10
    def extract_article_data(self, news_article_url):
        """
        Complex html data extraction of the full news article. Go 1 level deeper to the final news article.
        Read the low-levl data components/elements of the entire news article HTML news page.
        WARN: Data extract may be very specific to a single type/style of finance.yahoo.com news article.
        """

        # data elements extracted & computed
        # Authour, Date posted, Time posted, Age of article
        cmi_debug = __name__+"::"+self.extract_article_data.__name__+".#"+str(self.yti)
        logging.info('%s - IN' % cmi_debug )
        right_now = date.today()

        a_subset = self.news_article_depth_1(news_article_url)      # go DEEP into this 1 news HTML page & setup data extraction zones
        # print ( f"Tag sections in news page: {len(a_subset)}" )   # DEBUG
        for erow in range(len(a_subset)):       # cycyle through tag sections in this dataset (not predictible or consistent)
            if a_subset[erow].time:     # if this element rown has a <time> tag...
                nztime = a_subset[erow].time['datetime']
                ndate = a_subset[erow].time.text
                dt_ISO8601 = datetime.strptime(nztime, "%Y-%m-%dT%H:%M:%S.%fz")
                if a_subset[erow].div:  # if this element row has a sub <div>
                    nauthor = str( "{:.15}".format(a_subset[erow].div.find(attrs={'itemprop': 'name'}).text) )
                    # nauthor = a_subset[erow].div.find(attrs={'itemprop': 'name'}).text
                    #shorten down the above data element for the pandas DataFrame insert that happens later...

            if self.args['bool_xray'] is True:        # DEBUG Xray
                taglist = []
                for tag in a_subset[erow].find_all(True):
                    taglist.append(tag.name)
                print ( "Unique tags:", set(taglist) )

            logging.info('%s - Cycle: Follow News deep URL extratcion' % cmi_debug )

        # print ( f"Details: {ndate} / Time: {dt_ISO8601} / Author: {nauthor}" )        # DEBUG
        days_old = (dt_ISO8601.date() - right_now)
        date_posted = str(dt_ISO8601.date())
        time_posted = str(dt_ISO8601.time())
        # print ( f"News article age: DATE: {date_posted} / TIME: {time_posted} / AGE: {abs(days_old.days)}" )  # DEBUG
        return ( [nauthor, date_posted, time_posted, abs(days_old.days)] )  # return a list []

# method 11
    def news_article_depth_1(self, url):
        """
        Analyze 1 (ONE) individual news article taken from the list of articles for this stock.
        Set data extractor into KEY element zone within news article HTML dataset.
        Extract critical news elements, fields & data objects are full news artcile.
        Note: - called for each news article on the MAIN news page
        Note: - doing this recurisvely will be network expensive...but that is the plan
        """

        cmi_debug = __name__+"::"+self.news_article_depth_1.__name__+".#"+str(self.yti)
        logging.info('%s - IN' % cmi_debug )
        deep_url = url      # pass in the url that we want to deeply analyze
        logging.info( f'%s - Follow URL: {deep_url}' % (cmi_debug) )
        logging.info( '%s - Open/get() article data' % cmi_debug )
        with requests.Session() as s:
            nr = s.get(deep_url, stream=True, headers=self.yahoo_headers, cookies=self.yahoo_headers, timeout=5 )
            logging.info( f'%s - Read full HTML data with BS4: {deep_url}' % cmi_debug )
            nsoup = BeautifulSoup(nr.text, 'html.parser')
            logging.info( '%s - News article read complete!' % cmi_debug )
            # fnl_tag_dataset = soup.find_all('a')
            logging.info( '%s - Extract key elements/tags from HTML data' % cmi_debug )
            tag_dataset = nsoup.div.find_all(attrs={'class': 'D(tbc)'} )
            print ( f"{nr.text}" )
            logging.info( f'%s - close news article: {deep_url}' % cmi_debug )

        return tag_dataset
