import requests
from bs4 import BeautifulSoup
import re
import datetime
import os.path
import json
from utils import loadExistingAgendaList, writeAgendaListToDisk, downloadAgendas

def main():

	agency = "gavilan_ccd"
	gavilanScraper(agency)



'''
gavilanScraper
=======
Scrapes the agendas for the given agency, 
downloading the pdfs and creating a list of agendas.
Returns the list of agendas.
'''
def gavilanScraper(agency):
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

	base_url = "http://www.gavilan.edu/board/"

	# scrape meeting list page
	r = requests.get('http://www.gavilan.edu/board/agenda.php')
	meetings_soup = BeautifulSoup(r.content, "lxml")

	agenda_table = meetings_soup.find(id="agenda").find("table")
	agenda_rows = agenda_table.find("tbody").find_all("tr", valign="top")

	for row in agenda_rows:

		# extract the meeting date
		meeting_date_string = row.find("th").string
		meeting_date = datetime.datetime.strptime(meeting_date_string, "%B %d, %Y").date().strftime('%m-%d-%Y')

		# extract the agenda url
		rel_agenda_url = row.find("a", string="Agenda").get('href')
		agenda_url = base_url + rel_agenda_url

		# create an id
		agenda_id = "%s_%s" % (agency, meeting_date)

		if agenda_id not in [agenda["agenda_id"] for agenda in agenda_list]:
			print("New agenda found: %s, %s" % (agency, meeting_date))
			agenda_list.append({"agency": agency, "meeting_date": meeting_date, "agenda_id": agenda_id, "url": agenda_url, "downloaded": False, "parsed": False})

	return agenda_list
		
	










if __name__ == '__main__':
	main()