import requests
from bs4 import BeautifulSoup
import pickle
import re
import datetime
import os.path
import json
from utils import loadExistingAgendaList, writeAgendaListToDisk, downloadAgendas


def main():

	agency = "scc_boe"
	agency_code = "scccoe"

	agenda_list = loadExistingAgendaList(agency)
	agenda_list = getAgendasList(agency, agency_code, agenda_list)
	writeAgendaListToDisk(agency, agenda_list)


'''
getAgendasList
==============
Given an agency and the BoardDocs code for that agency,
return a list of meeting agendas posted on BoardDocs.
'''
def getAgendasList(agency, agency_code, agenda_list):

	# get list of meetings
	r = requests.get('http://www.boarddocs.com/ca/' + agency_code + '/Board.nsf/LT-GetMeetings')
	meetings_soup = BeautifulSoup(r.content, "lxml")

	# # write to disk to avoid hammering the server
	# pickle.dump(meetings_soup, open( "../docs/" + agency + "/data/test_meetings_html.p", "wb" ))
	# meetings_soup = pickle.load(open("../docs/" + agency + "/data/test_meetings_html.p", "rb" ))

	# extract links to agendas
	agenda_links = meetings_soup.find_all("a", class_="meeting")
	for link in agenda_links:

		meeting_title_raw = link.find_all("div")[-1].string
		meeting_title = cleanMeetingTitle(meeting_title_raw, agency)

		# # extract the meeting date
		meeting_date_string = link.find(string=re.compile(r'\w{3}\s\d+\,\s\d{4}'))
		meeting_date_string = re.sub(r'\(\w{3}\)', '', meeting_date_string).strip() # clean string
		meeting_date = datetime.datetime.strptime(meeting_date_string, "%b %d, %Y").date().strftime('%m-%d-%Y')

		# # extract the meeting id
		boarddocs_id = link['id']

		if boarddocs_id not in [agenda["boarddocs_id"] for agenda in agenda_list]:

			print("New agenda found: %s, %s" % (meeting_title, meeting_date))

			agenda_list.append({"agency": agency, "meeting_title": meeting_title, "meeting_title_raw": meeting_title_raw, "meeting_date": meeting_date, "boarddocs_id": boarddocs_id, "parsed": False})

	return agenda_list



'''
cleanMeetingTitle
=================
Remove unwanted boilerplate that some agencies attach to their agenda titles.
'''
def cleanMeetingTitle(raw_title, agency):

	if agency == "east_side_uhsd":
		meeting_title = raw_title.split("-", 1)[0].strip()
	else:
		meeting_title = raw_title

	return meeting_title











if __name__ == '__main__':
	main()