import json
import os
from scrapers.utils import buildDirectoryStructure, writeAgendaListToDisk
from scrapers import gavilan_scraper, board_docs_scraper, cupertino_usd_scraper
from parsers import board_docs_parser
from parsers.pdf_parser import parsePDFtoLines
from parsers.line_classifier import classifyAgendas
from parsers.line_structurer import structureLines

def main():

	agencies_list = getAgenciesList()
	for agency in agencies_list:
		print("=======================================================================")
		print("Now working on %s..." % agency['agency_id'])
		buildDirectoryStructure(agency['agency_id'], agency['agenda_type'])

		if agency['agenda_type'] == 'pdf':
			processPDFs(agency)

		elif agency['agenda_type'] == 'boarddocs':
			processBoardDocs(agency)

		else:
			print("That agenda type is not currently supported")


	





'''
getAgenciesList
===============
Load the json list of agencies if there is one,
otherwise return an empty list.
'''
def getAgenciesList():
	agencies_list = list()
	agencies_list_filepath = "agencies_list.json"
	if os.path.exists(agencies_list_filepath):
		with open(agencies_list_filepath) as data_file:
			agencies_list = json.load(data_file)

	return agencies_list



'''
processPDFs
===========
Scrape and process PDFs for a given agency.
'''
def processPDFs(agency):

	# scrape agency
	print("")
	print("SCRAPING PDFS...")
	if agency['agency_id'] == 'gavilan_ccd':
		agendas_list = gavilan_scraper.gavilanScraper(agency['agency_id'])
	elif agency['agency_id'] == 'cupertino_usd':
		agendas_list = cupertino_usd_scraper.scraper(agency['agency_id'])
	else:
		print("No scraper has been written for that agency")
		return

	# parse agenda lines
	print("")
	print("PARSING PDF LINES...")
	for agenda in agendas_list:
		if agenda['downloaded'] and not agenda['scanned'] and not agenda['parsed']:
			parsePDFtoLines(agency['agency_id'], agenda['meeting_date'], False)

	# train on a sample of agendas
	training_dir = "docs/%s/training_lines/" % agency['agency_id']
	num_training_files = len([f for f in os.listdir(training_dir) if f.endswith('.csv')])
	if num_training_files < 3:
		print("===========================")
		print("Please classify the lines in some sample agendas to train the classifier:")

		# classify the first, middle, and last agendas
		possible_training_agendas = [agenda for agenda in agendas_list if agenda['downloaded'] and not agenda['scanned']] # subset to parsable agendas
		training_agendas = [possible_training_agendas[0], possible_training_agendas[len(possible_training_agendas)//2], possible_training_agendas[-1]]
		for agenda in training_agendas:
			training_filename = "docs/%s/training_lines/%s_%s_training_lines.csv" % (agency['agency_id'], agency['agency_id'], agenda['meeting_date'])
			if not os.path.isfile(training_filename):
				parsePDFtoLines(agency['agency_id'], agenda['meeting_date'], True)

	# classify the agenda lines using the training set
	print("")
	print("CLASSIFYING PDF LINES...")
	if len([agenda for agenda in agendas_list if agenda['downloaded'] and not agenda['parsed'] and not agenda['scanned']]):
		agenda_dates = [agenda['meeting_date'] for agenda in agendas_list if agenda['downloaded'] and not agenda['parsed'] and not agenda['scanned']]
		classifyAgendas(agency['agency_id'], agenda_dates, False)

	# structure the classed agenda lines
	print("")
	print("STRUCTURING PDFS...")
	for agenda in agendas_list:
		if agenda['downloaded'] and not agenda['parsed'] and not agenda['scanned']:
			structureLines(agency['agency_id'], agenda['meeting_date'])
			agenda['parsed'] = True

	# write out the updated agendas list
	writeAgendaListToDisk(agency['agency_id'], agendas_list)



'''
processBoardDocs
===========
Scrape and process BoardDocs agendas for a given agency.
'''
def processBoardDocs(agency):

	# scrape agency
	print("")
	print("SCRAPING AGENDAS...")
	agendas_list = board_docs_scraper.scrapeBoardDocs(agency['agency_id'], agency['boarddocs_code'])

	# parse agendas
	print("")
	print("PARSING AGENDAS...")
	board_docs_parser.parseAgendas(agency['agency_id'], agency['boarddocs_code'])
















if __name__ == '__main__':
    main()