#!/usr/bin/python3
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import re
import logging
import argparse
import time
import threading
import json

# logging setup
logging.basicConfig(level=logging.INFO)

#####################################################

class y_techevents:
    """
    Class to extract Simple Today/Short/Medium/Long term indicator data set from finance.yahoo.com
    """

    # global accessors
    symbol = ""         # class global
    te_sentiment = {}   # Dict contains Tech Events elements...e.g.
                        # 0: ("today_only", "1D", Bullish/Bearish/Neutral or N/A )
                        # 1: ("short_term", "2W - 6W", Bullish/Bearish/Neutral or N/A )
                        # 2: ("med_term", "6W - 9M", Bullish/Bearish/Neutral or N/A )
                        # 3: ("long_term", "9M+", Bullish/Bearish/Neutral or N/A )
                        # 4: count_of_Bullish
    te_df0 = ""
    te_resp0 = ""
    te_jsondata0 = ""
    te_zone = ""
    te_short = ""
    te_mid = ""
    te_long = ""
    te_srs_zone = ""
    te_all_url = ""
    yti = 0
    cycle = 0           # class thread loop counter

    def __init__(self, yti):
        cmi_debug = __name__+"::"+self.__init__.__name__
        logging.info( f"{cmi_debug} - Instantiate.#{yti}" )
        self.te_df0 = pd.DataFrame(columns=[ 'Symbol', 'Today', 'Short', 'Mid', 'Long', 'Bullish', 'Time' ] )  # init empty DF with preset columns
        self.yti = yti
        return


# method #1
    def form_api_endpoints(self, symbol):
        """
        For Technical event Indicators endpoint for the req get()
        This page is where the Free view into some technical idicators are show with full TEXT strings descriptions.
        NOTE: This is a teaser page. Tech Events are only available to paid-for subscrption users. But the teaser page shows
        a clutch of free indicators...So we'll take the free Tech Event indicators, for now.
        1. Today, Short, intermediate, Long Term technical analysis
        2. Support, Resistance, Stop loss levels
        """
        cmi_debug = __name__+"::"+self.form_api_endpoints.__name__+".#"+str(self.yti)
        logging.info( f"{cmi_debug} - form API endpoint URL(s)" )
        self.symbol = symbol.upper()
        self.te_url = "https://finance.yahoo.com/chart/" + self.symbol + "?Technical="
        self.te_all_url = "https://finance.yahoo.com/quote/" + self.symbol + "?p=" + self.symbol + "&.tsrc=fin-srch"
        self.te_short_url = "https://finance.yahoo.com/chart/" + self.symbol + "?Technical=short"
        self.te_mid_url = "https://finance.yahoo.com/chart/" + self.symbol + "?Technical=intermediate"
        self.te_long_url = "https://finance.yahoo.com/chart/" + self.symbol + "?Technical=long"
        #
        logging.info( f"================================ Tech Events API endpoints ================================" )
        logging.info( f"{cmi_debug} - API endpoint #0: [ {self.te_url} ]" )
        logging.info( f"{cmi_debug} - API endpoint #1: [ {self.te_all_url} ]" )
        logging.info( f"{cmi_debug} - API endpoint #2: [ {self.te_short_url} ]" )
        logging.info( f"{cmi_debug} - API endpoint #3: [ {self.te_mid_url} ]" )
        logging.info( f"{cmi_debug} - API endpoint #4: [ {self.te_long_url} ]" )
        return


# method #2
    def get_te_zones(self, me):
        """
        Connect to finance.yahoo.com and extract (scrape) the raw JSON data out of
        the embedded webpage [finance.yahoo.com/chart/GOL?technical=short] html data table.
        Sabe JSON to class global attribute: self.te_resp0.text
        """
        cmi_debug = __name__+"::"+self.get_te_zones.__name__+".#"+str(self.yti)+"."+str(me)
        logging.info( f"{cmi_debug} - IN" )
        with requests.get( self.te_all_url, stream=True, timeout=5 ) as self.te_resp0:
            logging.info( f"{cmi_debug} - get() data / storing..." )
            self.soup = BeautifulSoup(self.te_resp0.text, 'html.parser')
            logging.info( f"{cmi_debug} - Data zone #1: [Entire page] {len(self.soup)} lines extracted / Done" )
        #
        logging.info( f"{cmi_debug} - Data zone #2: [chrt-evts-mod]..." )
        self.te_zone = self.soup.find(attrs={"id": "chrt-evts-mod"} )
        #logging.info( f"{cmi_debug} - Data zone #2: {len(self.te_zone)} lines extracted / Done" )

        logging.info( f"{cmi_debug} - Data zone #3: [<li>]..." )
        try:
            self.te_lizones = self.te_zone.find_all('li')
            #logging.info( f"{cmi_debug} - Data zone #3: {len(self.te_lizones)} lines extracted / Done" )
        except AttributeError as ae_inst:
            if ae_inst.__cause__ is None:       # interrogate error raised - was it for [NoneType]
                logging.info( f"{cmi_debug} - Data zone #3 / SCAN FAIL - EMPTY BS4 data" )
                return -1
                #self.te_today = self.te_zone.find(attrs={"class": "Fz(xs) Mb(4px)"}
            else:
                logging.info( f"{cmi_debug} - Data zone #3 / FAIL : {ae_inst.__cause__}" )
                return -2
        else:
            logging.info( f"{cmi_debug} - Data zone #4: [today]" )
            self.te_today = self.te_zone.find(attrs={"class": "W(1/4)--mobp W(1/2) IbBox"} )
            #logging.info( f"{cmi_debug} - Data zone #3: [today]" )
            #self.te_today_pat = self.te_zone.find(attrs={"class": "Mb(4px) Whs(nw)"} )
            return 0


# method #3
    def build_te_data(self, me):
        """
        Build-out Perfromance Outlook Technical Events dict
        Dict structure: { key: (embeded 5 element tuple) }
        e.g. {0: (te_sml, te_timeframe, "Grey", "Sideways", "Neutral") }
        1.  tme_sml : (Short/Medium/Long)
        2.  tm_timeframe : Time frame that this Tech Event covers (days/weeks/months)
        3.  Tech Event Indicator: Red/Grey/Green   * not included in final dict
        4.  Tech Event Indicator: Down/Sideways/Up *  not included in final dict
        5.  Tech Event Indicator: Bearish/Neutral/Bullish
        """
        cmi_debug = __name__+"::"+self.build_te_data.__name__+".#"+str(self.yti)+"."+str(me)

        logging.info( f"{cmi_debug} - CALLED" )
        time_now = time.strftime("%H:%M:%S", time.localtime() )
        logging.info( f"{cmi_debug} - Scan quote Tech Event indicators" )
        bullcount = 0
        y = 0   # current dict index
        te_today = self.te_today.next_element.next_element.string
        self.te_sentiment.update({y: ("Today", "1D", te_today)} )
        if te_today == "Bullish": bullcount += 1
        y += 1  # incr dict index
        for j in self.te_lizones:
            for i in j:
                te_strings = i.strings
                te_sml = next(te_strings)
                te_timeframe = next(te_strings)
                if i.svg is not None:
                    red = i.svg.parent.contents
                    red_down = re.search('180deg', str(red) )
                    grey_neutral = re.search('90deg', str(red) )
                    if red_down:        # Red Bearish
                        self.te_sentiment.update({y: (te_sml, te_timeframe, "Bearish")} )
                        y += 1          # incre dict index
                    elif grey_neutral:  # Grey Neutral
                        self.te_sentiment.update({y: (te_sml, te_timeframe, "Neutral")} )
                        y += 1          # incre dict index
                    else:               # Green Bullish
                        self.te_sentiment.update({y: (te_sml, te_timeframe, "Bullish")} )
                        bullcount += 1
                        y += 1          # incre dict index
                else:
                    pass
                    self.te_sentiment.update({y: (te_sml, te_timeframe, "N/A")} )
                    y += 1

        self.te_sentiment.update({y: bullcount} )
        logging.info('%s - populated new Tech Event dict' % cmi_debug )
        return y        # number of rows inserted into Tech events dict


# method #4
    def build_te_summary(self, combo_df, me):
        """
        Build a Perfromance Outlook Technical Events DataFrame that is...
        A nice eary to read summary table
        With Quick to identify stats on BUllish/Bearish Outlook
        And can be quickly visually correlated to the Master Summary DataFrame
        """
        cmi_debug = __name__+"::"+self.build_te_summary.__name__+".#"+str(self.yti)+"."+str(me)

        logging.info( f"{cmi_debug} - CALLED" )
        time_now = time.strftime("%H:%M:%S", time.localtime() )
        te_source = combo_df.list_uniques()    # work on the combo DataFrame (unique only, no DUPES)

        cols = 1
        print ( f"\n===== Build Bullish/Bearish outlook summary ==============================" )
        for this_sym in te_source['Symbol'].tolist():       # list of symbols to work on
            nq_symbol = this_sym.strip().upper()            # clearn each symbol (DF pads out with spaces)
            print ( f"{this_sym}...", end="", flush=True )
            self.form_api_endpoints(nq_symbol)
            te_status = self.get_te_zones(me)
            if te_status != 0:                              # FAIL : cant get te_zone data
                self.te_is_bad()                            # FAIL : build a FAILURE dict
                self.build_te_df(me)                        # FAIL: insert failure status into DataFrame for this symbol
                print ( f"!", end="", flush=True )
                logging.info( f"{cmi_debug} - FAILED to get Tech Event data: Clear all dicts" )
                self.te_sentiment.clear()
                cols += 1
            else:
                print ( f"+", end="", flush=True )      # GOOD : suceeded to get TE indicators
                self.build_te_data(me)
                self.build_te_df(me+1)      # debug helper, since we call method multiple times
                cols += 1

            if cols == 8:
                print ( f" " )              # only print 8 symbols per row
                cols = 1
            else:
                print ( f" / ", end="", flush=True )
            self.te_sentiment.clear()

        return


# method #5
    def te_is_bad(self):
        """
        Build a Technical Events dict showing all [ BAD / N/A ] indicators
        This method is leveraged if we experince issues scraping the TE indicators from the
        the Tech performance page/zones becasue they are flakey & unreliable. (yahoo wants you
        to pay for premium serivce to get access to them).
        Dict structure: { key: (embeded 5 element tuple) }
        e.g. {0: (te_sml, te_timeframe, "Grey", "Sideways", "Neutral") }
        1.  tme_sml : (Short/Medium/Long)
        2.  tm_timeframe : Time frame that this Tech Event covers (days/weeks/months)
        3.  Tech Event Indicator: - set to N/A
        4.  Tech Event Indicator: - set to N/A
        5.  Tech Event Indicator: - set to N/A
        """
        cmi_debug = __name__+"::"+self.te_is_bad.__name__+".#"+str(self.yti)

        logging.info( f"{cmi_debug} - CALLED" )
        time_now = time.strftime("%H:%M:%S", time.localtime() )
        logging.info( f"{cmi_debug} - Set ALL Tech Event indicators to BAD: N/A" )
        te_today = "N/A"
        self.te_sentiment.update({0: ("today_only", "1D", "N/A")} )
        self.te_sentiment.update({1: ("short_term", "2W - 6W", "N/A")} )
        self.te_sentiment.update({2: ("med_term", "6W - 9M", "N/A")} )
        self.te_sentiment.update({3: ("long_term", "9M+", "N/A")} )
        self.te_sentiment.update({4: 0})
        logging.info( f"{cmi_debug} - populated dict as BAD data: All values set to N/A" )
        return 4        # number of rows inserted into Tech events dict


# method #6
    def build_te_df(self, me):
        """
        Add a ROW into the sentiment DataFrame
        ROW is for current symbol last worked on, so method must *only* be called after
        you have sucessfullu built & populated the Tech Events sentiment dict.
        """

        cmi_debug = __name__+"::"+self.build_te_df.__name__+".#"+str(self.yti)+"."+str(me)
        logging.info( f"{cmi_debug} - CALLED" )
        time_now = time.strftime("%H:%M:%S", time.localtime() )
        logging.info( f"{cmi_debug} - Create Tech Event Perf DataFrame" )
        ####################################################################
        # craft final data structure.
        # NOTE: globally accessible and used by quote DF and quote DICT
        logging.info( f"{cmi_debug} - Build Dataframe dataset: {self.symbol}" )        # so we can access it natively if needed, without using pandas
        data0 = [[ \
           self.symbol, \
           self.te_sentiment[0][2], \
           self.te_sentiment[1][2], \
           self.te_sentiment[2][2], \
           self.te_sentiment[3][2], \
           self.te_sentiment[4], \
               time_now ]]
        # self.te_df0.drop(self.te_df0.index, inplace=True)        # ensure the DF is empty
        logging.info( f"{cmi_debug} - Populate DF with Tech Events emphemerial dict data" )
        te_temp_df0 = pd.DataFrame(data0, columns=[ 'Symbol', 'Today', 'Short', 'Mid', 'Long', 'Bullish', 'Time' ] )
        self.te_df0 = self.te_df0.append(te_temp_df0, ignore_index=True)
        logging.info( f"{cmi_debug} - Tech Event DF created" )
        return

# method #7
    def reset_te_df0(self):
        """
        Reset DataFrame index to be sequential, sarting from 0
        """
        cmi_debug = __name__+"::"+self.reset_te_df0.__name__+".#"+str(self.yti)
        logging.info( f"{cmi_debug} - CALLED" )
        self.te_df0.reset_index(inplace=True, drop=True)
        logging.info( f"{cmi_debug} - completed" )
        return


# method #8
    def te_into_nquote(self, nqinst):
        """
        Push the core Tech Event Indicators into their location within the nasdaq quote dict
        """
        cmi_debug = __name__+"::"+self.te_into_nquote.__name__+".#"+str(self.yti)
        logging.info( f"{cmi_debug} - CALLED" )
        nqinst.quote.update({"today_only": self.te_sentiment[0][2]} )
        nqinst.quote.update({"short_term": self.te_sentiment[1][2]} )
        nqinst.quote.update({"med_term": self.te_sentiment[2][2]} )
        nqinst.quote.update({"long_term": self.te_sentiment[3][2]} )
        nqinst.quote.update({"Bull_count": self.te_sentiment[4]} )
        logging.info( f"{cmi_debug} - completed" )
        return
