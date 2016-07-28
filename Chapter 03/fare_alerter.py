import sys
import pandas as pd
import numpy as np
import requests
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import schedule
import time

def check_flights():
	url = "https://www.google.com/flights/explore/#explore;f=JFK,EWR,LGA;t=HND,NRT,TPE,HKG,KIX;s=1;li=8;lx=12;d=2016-04-01"
	driver = webdriver.PhantomJS()
	dcap = dict(DesiredCapabilities.PHANTOMJS)
	dcap["phantomjs.page.settings.userAgent"] = \
	("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36")
	driver = webdriver.PhantomJS(desired_capabilities=dcap, service_args=['--ignore-ssl-errors=true'])
	driver.get(url)
	wait = WebDriverWait(driver, 20)
	wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "span.FTWFGDB-v-c")))

	s = BeautifulSoup(driver.page_source, "lxml")

	best_price_tags = s.findAll('div', 'FTWFGDB-w-e')

	# check if scrape worked - alert if it fails and shutdown
	if len(best_price_tags) < 4:
		print('Failed to Load Page Data')
		 requests.post('https://maker.ifttt.com/trigger/fare_alert/with/key/MY_SECRET_KEY',\
		 data={ "value1" : "script", "value2" : "failed", "value3" : "" })
		sys.exit(0)
	else:
		print('Successfully Loaded Page Data')

	best_prices = []
	for tag in best_price_tags:
	    best_prices.append(int(tag.text.replace('$','')))

	best_price = best_prices[0]

	best_height_tags = s.findAll('div', 'FTWFGDB-w-f')
	best_heights = []
	for t in best_height_tags:
	    best_heights.append(float(t.attrs['style']\
	                              .split('height:')[1].replace('px;','')))

	best_height = best_heights[0]

	# price per pixel of height
	pph = np.array(best_price)/np.array(best_height)

	cities = s.findAll('div', 'FTWFGDB-w-o')

	hlist=[]
	for bar in cities[0]\
	    .findAll('div', 'FTWFGDB-w-x'):
	    hlist.append(float(bar['style']\
	                       .split('height: ')[1].replace('px;','')) * pph)

	fares = pd.DataFrame(hlist, columns=['price'])
	px = [x for x in fares['price']]
	ff = pd.DataFrame(px, columns=['fare']).reset_index()

	# begin the clustering
	X = StandardScaler().fit_transform(ff)
	db = DBSCAN(eps=1.5, min_samples=1).fit(X)

	labels = db.labels_
	clusters = len(set(labels))

	pf = pd.concat([ff,pd.DataFrame(db.labels_,
	                                columns=['cluster'])], axis=1)

	rf = pf.groupby('cluster')['fare'].agg(['min','count']).sort_values('min', ascending=True)

	# set up our rules
	# must have more than one cluster
	# cluster min must be equal to lowest price fare
	# cluster size must be less than 10th percentile
	# cluster must be $100 less the next lowest-priced cluster
	if clusters > 1 and ff['fare'].min() == rf.iloc[0]['min']\
	 and rf.iloc[0]['count'] < rf['count'].quantile(.10)\
	  and rf.iloc[0]['fare'] + 100 < rf.iloc[1]['fare']:
		city = s.find('span','FTWFGDB-v-c').text
		fare = s.find('div','FTWFGDB-w-e').text
		r = requests.post('https://maker.ifttt.com/trigger/fare_alert/with/key/MY_SECRET_KEY',\
		 data={ "value1" : city, "value2" : fare, "value3" : "" })
	else:
		print('no alert triggered')

# set up the scheduler to run our code every 60 min
schedule.every(60).minutes.do(check_flights)

while 1:
    schedule.run_pending()
    time.sleep(1)



