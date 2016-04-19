import csv
import re

def main():

	agency = "east_side_uhsd"
	date = "1-21-16"

	# read in classed lines
	lines = loadLines(agency, date)

	# position variables
	active_item = False

	structured_agenda = list()

	item_info = { \
		"meeting_part": "", \
		"agenda_section": "", \
		"item_text": "" \
	}

	# loop over lines, converting to a structured format
	for i, line in enumerate(lines):
		# meeting part
		if line["line_class"] == "meeting_heading":
			# set meeting part
			item_info["meeting_part"] = line["text"]

			# reset active item flag to false
			active_item = False

		# section heading
		elif line["line_class"] == "section_heading":
			# set agenda section
			item_info["agenda_section"] = line["text"]

			# reset active item flag to false
			active_item = False

		# first line of an item
		elif line["line_class"] == "item_heading":

			# new item, add the previous one to the structured agenda list
			structured_agenda.append(item_info)

			# start new item text entry
			item_info["item_text"] = line["text"]

			# set active_item flag
			active_item = True

		elif line["line_class"] == "item_text":
			if active_item:
				item_info["item_text"] += line["text"]
			else:
				# throw warning
				print("PARSE ERROR")
				print("Line classified as item text (" + line["text"] + " found outside of an agenda item")

		elif line["line_class"] == "other_text":
			# ignore it unless there is an open agenda item, then explore it in more detail
			if active_item:
				print(line["text"])


	for entry in structured_agenda:
		print(entry)



			




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



if __name__ == '__main__':
    main()