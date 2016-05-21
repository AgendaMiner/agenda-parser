import json
import os
import requests


'''
buildDirectoryStructure
=======================
Given a shorthand name for an agency and the type of agenda 
it uses, create the necessary subdirectories within the docs folder.
'''
def buildDirectoryStructure(agency, agenda_type):

	# create base directory
	base_dir = "../docs/%s" % agency
	if not os.path.exists(base_dir):
		os.makedirs(base_dir)

	# create structured agendas subdirectory
	agendas_dir = base_dir + "/structured_agendas"
	if not os.path.exists(agendas_dir):
		os.makedirs(agendas_dir)

	# create additional directories if agenda type is pdf
	if agenda_type == "pdf":

		pdf_dirs = list()
		pdf_dirs.append(base_dir + "/data")
		pdf_dirs.append(base_dir + "/classed_lines")
		pdf_dirs.append(base_dir + "/parsed_lines")
		pdf_dirs.append(base_dir + "/raw_pdfs")
		pdf_dirs.append(base_dir + "/training_lines")
		
		for dir in pdf_dirs:
			if not os.path.exists(dir):
				os.makedirs(dir)



'''
loadExistingAgendaList
==================
Check if there is a saved list of agendas for this agency.
Return the list if it exists, otherwise return an empty list.
'''
def loadExistingAgendaList(agency):

	agenda_list = list()
	agenda_list_filepath = "../docs/" + agency + "/agenda_list.json"
	if os.path.exists(agenda_list_filepath):
		with open(agenda_list_filepath) as data_file:
			agenda_list = json.load(data_file)

	return agenda_list



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



'''
downloadAgendas
===============
Given a list of agendas and the URLs of their pdfs, scrapes any agendas that haven't
yet been downloaded. Updates the agenda list, and returns it.
'''
def downloadAgendas(agency, agenda_list):
	for agenda in agenda_list:

		if not agenda['downloaded']:

			r = requests.get(agenda['url'])
			pdf_filepath = "../docs/" + agency + "/raw_pdfs/" + agenda['agenda_id'] + ".pdf"
			with open(pdf_filepath, 'wb') as f:
				f.write(r.content)

			agenda['downloaded'] = True

	return agenda_list