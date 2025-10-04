from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time

def main():
	options=Options()
	options.add_argument("--headless")  # run without browser window
	driver=webdriver.Chrome(options=options)

	url="https://leetcode.com/u/satkuri_Kailash/"
	driver.get(url)

	# wait for JS to render
	time.sleep(3)

	html=driver.page_source
	driver.quit()

	soup=BeautifulSoup(html,"html.parser")

	# Example: print main header text (may vary depending on site HTML)
	title=soup.find("title")
	if title:
		print("Page Title:",title.get_text().strip())
	else:
		print("No <title> tag found")

if __name__=="__main__":
	main()
