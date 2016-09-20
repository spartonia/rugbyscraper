# Rugby Scraper

## Instructions 
The scraper runs on Python 2.7 and MongoDB. Python 2.7 is installed by default 
on Mac. To verify, open a terminal window and type
```python
python --version
```
We also need MongoDB installed. Please refer to [momgoDB installation guide](https://docs.mongodb.com/manual/tutorial/install-mongodb-on-os-x/)

## Installation 
Open a termonal and go to folder `rugbyscraper` where it contains `rugbyscraper` and 
 `scrapy.cfg` and `requirements.txt`. In the terminal enter the following:
 
```
sudo easy_install pip
```
and then 
```
pip install requirements.txt
```
wait until all requirements are installed, then we are done. 

###  Using scraper 
In the terminal go to `rugbyscraper` folder as wee did in installation step. Enter the following command and scraping will start. 
```
scrapy crawl historic
```
now you should be able to scaping starts. It will take one to several hours for scraping job to be done. Once scraping is done, we can verify the database to see scraped data. In the terminal open mongoDB by typing
```
mongo
```
in the shell, enter
```
use Rugby
```
and then 
```
db.result.findOne()
```
will grab a item from results. 
If you have difficulty using mongoDB shell, you can doenload and install GUI admin which is available for Mac [here](https://docs.mongodb.com/ecosystem/tools/administration-interfaces/) (Disclaimer: I have not used it myself).
