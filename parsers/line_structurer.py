import csv
import re
import json
import codecs

def main():

	agency = "east_side_uhsd"
	date = "1-21-16"

	structureLines(agency, date)



'''
structureLines
==============
Given an agency and a meeting date,
converts the output from the line-structurer into 
a JSON representation of the meeting agenda.
'''
def structureLines(agency, date):
	lines = loadLines(agency, date)
	json_agenda = convertLinesToJSON(agency, date, lines)
	json_agenda = cleanExtractJSON(json_agenda)

	print(json.dumps(json_agenda, indent=4))

	writeJSONtoDisk(json_agenda, agency, date, "TODO INSERT TITLE")


'''
loadLines
=========
Given an agency and a meeting date,
load the classed lines CSV into a list of dicts
'''
def loadLines(agency, date):
	lines = list()
	lines_filepath = "../docs/" + agency + "/classed_lines/" + agency + "_" + date + "_classed_lines.csv"

	with open(lines_filepath) as lines_file:
		lines_reader = csv.DictReader(lines_file)
		for row in lines_reader:
			lines.append(row)

	return lines


'''
extractSectionNumber
====================
Checks if the start of the line matches any of the known regex patterns for section numbers.
Return the number if one is found, False otherwise.
'''
def extractSectionNumber(line_text):

	# try to find a section number
	re_starts_num_or_letter = re.compile(r'\d+\.?\s+|[A-Za-z][.)]?\s+')
	if re_starts_num_or_letter.match(line_text) is not None:
		raw_num_string = re_starts_num_or_letter.match(line_text).group()
	else:
		return False

	# clean the section number
	num_string = raw_num_string.strip() # remove whitespace
	num_string = re.sub(r'^\s?[.)]', '', num_string) # remove dots and )

	return num_string


'''
extractItemNumber
====================
Checks if the start of the line matches any of the known regex patterns for item numbers.
Return the number if one is found, False otherwise.
'''
def extractItemNumber(line_text):

	# regex options to try
	re_starts_num_or_letter = re.compile(r'\d+[.)]?\s+|[A-Za-z][.)]?\s+')
	re_starts_sub_num = re.compile(r'\d+[\.]\d+\s+')
	re_starts_num_letter = re.compile(r'\d+[\.][A-Za-z]\s+')

	# try to find a item number
	if re_starts_num_or_letter.match(line_text) is not None:
		raw_num_string = re_starts_num_or_letter.match(line_text).group()
		raw_num_string = re.sub(r'^\s?[.)]', '', raw_num_string)
	elif re_starts_sub_num.match(line_text) is not None:
		raw_num_string = re_starts_sub_num.match(line_text).group()
	elif re_starts_num_letter.match(line_text) is not None:
		raw_num_string = re_starts_num_letter.match(line_text).group()
	else:
		return False

	# clean the section number
	num_string = raw_num_string.strip() # remove whitespace

	return num_string

'''
convertLinesToJSON
==================
Given a list of classified lines, convert them into a heirarchical JSON object.
Return the object.
'''
def convertLinesToJSON(agency, date, lines):

	# init active item flag
	active_item = False

	# init json object
	json_agenda = {
		"agency": agency, \
		"meeting_date": date, \
		"meeting_parts": []
	}

	# loop over lines, converting to a structured format
	for i, line in enumerate(lines):
		# meeting part
		if line["line_class"] == "meeting_heading":
			
			# add section to json
			json_agenda["meeting_parts"].append({"meeting_part": line["text"], "agenda_sections": []})

			# set flags
			active_item = False

		# section heading
		elif line["line_class"] == "section_heading":

			# check if there is a meeting part, add a full_meeting placeholder if not
			if len(json_agenda["meeting_parts"]) == 0:
				json_agenda["meeting_parts"].append({"meeting_part": "full_meeting", "agenda_sections": []})

			json_agenda["meeting_parts"][-1]["agenda_sections"].append({"section_name_raw": line["text"], "section_number": "", "items": []})

			# reset active item flag to false
			active_item = False

		# first line of an item
		elif line["line_class"] == "item_heading":

			json_agenda["meeting_parts"][-1]["agenda_sections"][-1]["items"].append({"item_text_raw": line["text"], "item_number": ""})

			# set active_item flag
			active_item = True

		# additional lines of item text
		elif line["line_class"] == "item_text":
			if active_item:
				json_agenda["meeting_parts"][-1]["agenda_sections"][-1]["items"][-1]["item_text_raw"] += line["text"]

			else:
				# throw warning
				print("PARSE ERROR")
				print("Line classified as item text (" + line["text"] + " found outside of an agenda item")

		elif line["line_class"] == "other_text":
			# ignore it unless there is an open agenda item, then explore it in more detail
			if active_item:
				if lines[i+1] == "item_text": # if the next line is text, this is probably an empty line
					json_agenda["meeting_parts"][-1]["agenda_sections"][-1]["items"][-1]["item_text_raw"] += "\n"

	return json_agenda



'''
cleanExtractJSON
================
Given a structured agenda as a JSON object, extract item numbers, etc and clean up the text.
Returns a processed version of the JSON object.
'''
def cleanExtractJSON(json_agenda):

	for meeting_part in json_agenda["meeting_parts"]:
		for agenda_section in meeting_part["agenda_sections"]:

			# try to extract the section number
			section_name = agenda_section["section_name_raw"]
			section_number = extractSectionNumber(section_name)
			if section_number:
				agenda_section["section_number"] = section_number

				# strip the section number from the section name
				section_name = section_name.replace(section_number, "", 1)
				section_name = re.sub(r'^\.', "", section_name) # remove any remaining dot at the start of the line

			section_name = section_name.strip()
			agenda_section["section_name"] = section_name

			for item in agenda_section["items"]:

				# try to extract the item number
				item_text = item["item_text_raw"]
				item_number = extractItemNumber(item_text)
				if item_number:
					item["item_number"] = item_number

					# strip the item number from the item text
					item_text = item_text.replace(item_number, "", 1)
					item_text = re.sub(r'^\.', "", item_text) # remove any remaining dot at the start of the line

				item_text = item_text.strip()
				item["item_text"] = item_text


	return json_agenda



'''
writeJSONtoDisk
===============
Given a JSON-formatted agenda object, an agency name, and a date,
writes out the object to disk as JSON
'''
def writeJSONtoDisk(json_agenda, agency, date, meeting_title):
	filepath = "../docs/" + agency + "/structured_agendas/" + agency + "_" + date + "_" + meeting_title + "_agenda.json"

	with codecs.open(filepath, 'w', encoding="utf-8") as outfile:
		json.dump(json_agenda, outfile, sort_keys = True, indent = 4, ensure_ascii=False)




if __name__ == '__main__':
    main()