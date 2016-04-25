import docx
import json
import re
import datetime
import codecs

def main():
	filename = "AgendaReport_2015Aug14.docx"

	parseTrainingDoc(filename)




'''
parseTrainingDoc
===============
Given the name of a word document containing agenda items
that have been deemed to be interesting, extract sufficient information 
to match them with the original agenda items.
Return a JSON-formatted version of the document.
'''
def parseTrainingDoc(filename):

	# load document
	doc_filepath = "../docs/training_data/raw_docs/" + filename
	doc = docx.Document(doc_filepath)

	classed_paras = classifyDocParas(doc)
	json_doc = extractInfoFromDoc(classed_paras)
	writeDocToDisk(json_doc, filename)


'''
classifyDocParas
================
Given a document object, classify each paragraph
to help with parsing later.
Return a JSON-formatted list of classified paragraphs.
'''
def classifyDocParas(doc):

	classed_paras = []

	for i, para in enumerate(doc.paragraphs):

		para_object = {"text": para.text, "line_type": "text"}

		# see if this matches the format for different lines
		if re.match(r'Agenda Item Name:|Item Name:', para.text):
			para_object['line_type'] = "name"
			if i - 2 > 0:
				classed_paras[i-2]['line_type'] = 'heading' # update the preceeding heading

		elif re.match(r'Agenda Number:', para.text):
			para_object['line_type'] = 'number'
		elif re.match(r'Public entity:', para.text):
			para_object['line_type'] = 'agency'
		elif re.match(r'Date/time/location of meeting:', para.text):
			para_object['line_type'] = 'date_time'
		elif re.match(r'Issue summary:', para.text):
			para_object['line_type'] = 'summary'

		classed_paras.append(para_object)

	return classed_paras



'''
extractInfoFromDoc
==================
Given a JSON-formatted list of classed paragraphs,
extract the information necessary to match each
item up to the original agenda item.
Return a new JSON-formatted list of items.
'''
def extractInfoFromDoc(classed_paras):

	json_doc = []

	for para in classed_paras:
		if para['line_type'] == 'heading':

			priorities = extractPriorities(para['text'])

			json_doc.append({'agency': '', \
				'meeting_date': '', \
				'item_name': '', \
				'item_number': '', \
				'priority_wpusa': priorities['wpusa'], \
				'priority_sblc': priorities['sblc'], \
				'priority_unite': priorities['unite'], \
				'priority_ibew': priorities['ibew']})

		elif para['line_type'] == 'name':
			json_doc[-1]['item_name'] = re.sub(r'Agenda Item Name:|Item Name:', '', para['text']).strip()

		elif para['line_type'] == 'number':
			json_doc[-1]['item_number'] = re.sub(r'Agenda Number:', '', para['text']).strip()

		elif para['line_type'] == 'agency':
			json_doc[-1]['agency'] = re.sub(r'Public entity:', '', para['text']).strip()

		elif para['line_type'] == 'date_time':
			date_string = re.sub(r'Date/time/location of meeting:', '', para['text']).strip()
			date_regex = re.match(r'\w{3}\.\s\d+,\s\d{4}', date_string)
			if date_regex:
				json_doc[-1]['meeting_date'] = datetime.datetime.strptime(date_regex.group(), "%b. %d, %Y").date().strftime('%m-%d-%Y')

	return json_doc
	# print(json.dumps(json_doc, indent=4))



'''
extractPriorities
=================
Given a heading, extract the clients and the priority that item had for each.
Return a dict of priorites.
'''
def extractPriorities(text):

	priorities = {
		'wpusa': None,
		'sblc': None,
		'ibew': None,
		'unite': None
	}

	# extract the (for ...) part of the line
	for_string = ""

	for_regex = re.search(r'\(for.+\)|\(.*yellow.*\)\s?$|\(.*blue.*\)\s?$', text)
	if for_regex:
		for_string = for_regex.group()
		for_string = re.sub(r'\(for|\)', '', for_string).strip().lower()

		# check if coded yellow for any clients
		if 'yellow' in for_string:
			for_split = for_string.split("yellow")
			yellow_clients = for_split[0]

			if len(for_split) > 1:
				blue_clients = re.sub(r'^,|blue', '', for_split[1]).strip()
		elif 'blue' in for_string:
			yellow_clients = ""
			blue_clients = re.sub('blue', '', for_string)

		# check the clients against the yellow and blue client strings
		if 'wpusa' in yellow_clients:
			priorities['wpusa'] = 'yellow'
		elif 'wpusa' in blue_clients:
			priorities['wpusa'] = 'blue'

		if 'sblc' in yellow_clients:
			priorities['sblc'] = 'yellow'
		elif 'sblc' in blue_clients:
			priorities['sblc'] = 'blue'

		if 'ibew' in yellow_clients:
			priorities['ibew'] = 'yellow'
		elif 'ibew' in blue_clients:
			priorities['ibew'] = 'blue'

		if 'unite' in yellow_clients:
			priorities['unite'] = 'yellow'
		elif 'unite' in blue_clients:
			priorities['unite'] = 'blue'

		if 'all' in yellow_clients:
			priorities['wpusa'] = 'yellow'
			priorities['sblc'] = 'yellow'
			priorities['ibew'] = 'yellow'
			priorities['unite'] = 'yellow'
		elif 'all' in blue_clients:
			priorities['wpusa'] = 'blue'
			priorities['sblc'] = 'blue'
			priorities['ibew'] = 'blue'
			priorities['unite'] = 'blue'

	else:
		print("ERROR - COULD NOT FIND CLIENTS")
		print(text)

	return priorities


'''
writeDocToDisk
==============
Save out the JSON-formatted agenda report to disk.
'''
def writeDocToDisk(json_doc, original_filename):

	# extract date from original filename
	date_regex = re.search(r'\d{4}\w{3}\d+', original_filename)
	if date_regex:
		date_string = date_regex.group()

		json_filepath = "../docs/training_data/structured_reports/%s.json" % date_string
		with codecs.open(json_filepath, 'w', encoding="utf-8") as outfile:
			json.dump(json_doc, outfile, sort_keys = True, indent = 4, ensure_ascii=False)

	else:
		print("ERROR - COULD NOT PARSE DATE STRING FROM THE FILENAME")
		print(original_filename)














if __name__ == '__main__':
    main()