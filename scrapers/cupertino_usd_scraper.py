import requests
from bs4 import BeautifulSoup
import re
import datetime
import os.path
import json
from utils import loadExistingAgendaList, writeAgendaListToDisk, downloadAgendas

def main():

	agency = "cupertino_usd"
	scraper(agency)



'''
scraper
=======
Scrapes the agendas for the given agency, 
downloading the pdfs and creating a list of agendas.
Returns the list of agendas.
'''
def scraper(agency):
	agenda_list = loadExistingAgendaList(agency)
	agenda_list = getAgendasList(agency, agenda_list)
	agenda_list = downloadAgendas(agency, agenda_list)
	writeAgendaListToDisk(agency, agenda_list)
	return agenda_list



'''
getAgendasList
==============
Scrapes a list of meetings and their agenda PDF urls.
Returns the list.
'''
def getAgendasList(agency, agenda_list):

	### no easy way to scrape this properly, so instead try scraping every possible date

	# start_date = datetime.date(2013,1,1)
	# find the most recent date in the agendas list
	agenda_dates = [datetime.datetime.strptime(agenda['meeting_date'],'%m-%d-%Y') for agenda in agenda_list]
	start_date = max(agenda_dates).date()
	end_date = datetime.date.today()
	delta = end_date - start_date

	for i in range(delta.days + 1):
		date_obj = start_date + datetime.timedelta(days=i)
		year = int(date_obj.strftime('%y'))
		prev_year = year - 1
		next_year = year + 1

		# build urls for either option
		url_opt_1 = "http://www.cusdk8.org/edline/about/board/agendas/{0}{1}/Board%20Agenda%20-%20Public%20{2}.pdf".format(prev_year, year, date_obj.strftime('%m%d%y'))
		url_opt_2 = "http://www.cusdk8.org/edline/about/board/agendas/{0}{1}/Board%20Agenda%20-%20Public%20{2}.pdf".format(year, next_year, date_obj.strftime('%m%d%y'))

		# see if either url returns a valid file
		valid_url = None
		r = requests.get(url_opt_1)
		if r.status_code == 200:
			valid_url = url_opt_1
		else:
			r = requests.get(url_opt_2)
			if r.status_code == 200:
				valid_url = url_opt_2

		if valid_url:
			# extract the meeting date
			meeting_date = date_obj.strftime('%m-%d-%Y')

			# create an id
			agenda_id = "%s_%s" % (agency, meeting_date)

			if agenda_id not in [agenda["agenda_id"] for agenda in agenda_list]:
				print("New agenda found: %s, %s" % (agency, meeting_date))
				agenda_list.append({"agency": agency, "meeting_date": meeting_date, "agenda_id": agenda_id, "url": valid_url, "downloaded": False, "scanned": False, "parsed": False})

	return agenda_list
		
	










if __name__ == '__main__':
	main()