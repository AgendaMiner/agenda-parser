import requests
from bs4 import BeautifulSoup
import pickle
import re
import os.path
import json
import line_structurer

def main():

	agency = "san_jose_evergreen_ccd"
	agency_code = "sjeccd"

	parseAgendas(agency, agency_code)

	

'''
parseAgendas
============
'''
def parseAgendas(agency, agency_code):

	agenda_list = loadAgendaList(agency)
	for agenda in agenda_list:

		if not agenda['parsed']:

			agenda_outline = parseAgendaOutline(agency, agency_code, agenda)

			json_agenda = {
				"agency": agency,
				"meeting_date": agenda['meeting_date'],
				"meeting_sections": []
			}

			for section in agenda_outline:
				json_agenda['meeting_sections'].append(structureAgendaSection(agency, agency_code, section))

			print(json.dumps(json_agenda, indent=4))

			# clean up the meeting title
			clean_title = agenda['meeting_title'].strip().lower()
			clean_title = re.sub(r'\W+', '_', clean_title)
			line_structurer.writeJSONtoDisk(json_agenda, agency, json_agenda['meeting_date'], clean_title)

			agenda['parsed'] = True

	writeAgendaListToDisk(agency, agenda_list)


'''
loadAgendaList
==================
Read in the list of agenda items for the given agency.
'''
def loadAgendaList(agency):

	agenda_list_filepath = "../docs/" + agency + "/agenda_list.json"
	if os.path.exists(agenda_list_filepath):
		with open(agenda_list_filepath) as data_file:
			agenda_list = json.load(data_file)
	else:
		print("ERROR - NO AGENDA LIST FOUND")

	return agenda_list



'''
parseAgendaOutline
==============
Given the BoardDocs code for an agency and a dict containing the agenda id,
parse the agenda to extract section headings and item ids.
Return the JSON-formatted agenda outline.
'''
def parseAgendaOutline(agency, agency_code, agenda_info):

	agenda_id = agenda_info['boarddocs_id']

	# # get agenda
	r = requests.get('http://www.boarddocs.com/ca/' + agency_code + '/Board.nsf/LT-GetAgenda', params={'open': '', 'id': agenda_id})
	agenda_soup = BeautifulSoup(r.content, "lxml")

	# write to disk to avoid hammering the server
	# pickle.dump(r.content, open("../docs/" + agency + "/data/test_agenda_html.p", "wb" ))
	# content = pickle.load(open("../docs/" + agency + "/data/test_agenda_html.p", "rb" ))
	# agenda_soup = BeautifulSoup(content, "lxml")

	# init json object
	items_structure = list()

	# extract each agenda section heading
	agenda_section_headings = agenda_soup.find_all("div", class_="category")
	for heading in agenda_section_headings:
		heading_text = heading.find("span", class_="category-name").string
		heading_id = heading['id']

		items_structure.append({'heading': heading_text, 'heading_id': heading_id, 'item_ids': []})

		# get items until next heading
		heading_wrapper = heading.find_parent("div", class_="wrap-category")
		next_element = heading_wrapper.find_next_sibling('div')
		while next_element is not None and "wrap-category" not in next_element['class']:

			# add the item to the items structure list
			items_structure[-1]['item_ids'].append(next_element['id'])

			# advance list
			next_element = next_element.find_next_sibling('div')

	return items_structure


'''
structureAgendaSection
======================
Given a dict with info about an agenda section,
generate a JSON-formatted dict with info on that section and its items.
Return the JSON object.
'''
def structureAgendaSection(agency, agency_code, section):

	section_info = parseItemText(section['heading'], agency, True)

	json_section = {
		"section_name": section_info['item_text'],
		"section_number": section_info['item_number'],
		"items": []
	}

	for item_id in section['item_ids']:
		json_section['items'].append(parseAgendaItem(agency, agency_code, item_id))

	return json_section


'''
parseAgendaItem
===============
Given a board docs agency code and an item id, 
parse that item into a structured dict. Return the dict.
'''
def parseAgendaItem(agency, agency_code, item_id):

	# get agenda item
	r = requests.get('http://www.boarddocs.com/ca/' + agency_code + '/Board.nsf/LT-GetAgendaItem', params={'open': '', 'id': item_id})
	item_soup = BeautifulSoup(r.content, "lxml")

	# write to disk to avoid hammering the server
	# pickle.dump(r.content, open("../docs/" + agency + "/data/test_agenda_item_html.p", "wb" ))
	# content = pickle.load(open("../docs/" + agency + "/data/test_agenda_item_html.p", "rb" ))
	# item_soup = BeautifulSoup(content, "lxml")

	item_content = { \
		'item_number': '', \
		'item_text_raw': '', \
		'item_text': '', \
		'item_details': '', \
		'item_type': '', \
		'item_recommendation': '',\
		'boarddocs_id': item_id \
	}

	item_content['item_text_raw'] = ''.join(item_soup.find('div', id="ai-name").strings)
	cleaned_text = parseItemText(item_content['item_text_raw'], agency, False)
	item_content['item_number'] = cleaned_text['item_number']
	item_content['item_text'] = cleaned_text['item_text']

	# extract item details
	details = ''.join(item_soup.find('div', key="publicbody").strings)
	item_content['item_details'] = re.sub(r'[\n]+', '\n', details) # strip extra line breaks

	# extract recommendation, if any
	rec_heading = item_soup.find(string=re.compile("Recommended Action"))
	if rec_heading is not None:
		item_content['item_recommendation'] = rec_heading.parent.find_next_sibling('div').string

	# extract item type
	type_heading = item_soup.find(string=re.compile("Type"))
	if type_heading is not None:
		item_content['item_type'] = type_heading.parent.find_next_sibling('div').string

	return item_content


'''
parseItemText
=================
Check if the raw item text string starts with a number. 
If so, extract the number and clean the rest of the string.
Return a dict with the number (if any) and the cleaned string.
'''
def parseItemText(raw_text, agency, is_section_heading):

	cleaned_text = {'item_number': '', 'item_text': ''}

	# try to extract an item number
	if is_section_heading:
		item_number = line_structurer.extractSectionNumber(raw_text.strip())
	else:
		item_number = line_structurer.extractItemNumber(raw_text.strip())
	if item_number:
		cleaned_text['item_number'] = item_number

		# strip the item number from the text string
		raw_text = raw_text.replace(item_number, "")
		raw_text = re.sub(r'^\s?[.)]', '', raw_text)

	# strip whitespace
	cleaned_text['item_text'] = raw_text.strip()

	return cleaned_text
	


'''
writeAgendaListToDisk
=====================
Given an agency and JSON-formatted agenda list,
write out the list to disk.
'''
def writeAgendaListToDisk(agency, agenda_list):

	agenda_list_filepath = "../docs/" + agency + "/agenda_list.json"
	with open(agenda_list_filepath, 'wb') as outfile:
		json.dump(agenda_list, outfile, sort_keys = True, indent = 4, ensure_ascii=False)








if __name__ == '__main__':
	main()