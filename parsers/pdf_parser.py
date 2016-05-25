import re
import csv
import pprint
import os.path
import pickle
import pandas as pd
import pdfplumber
from operator import itemgetter
from collections import Counter
from sklearn.feature_extraction.text import CountVectorizer

pp = pprint.PrettyPrinter(indent=4)

def main():

	agency = "cupertino_usd"
	date = "04-05-2016"

	parsePDFtoLines(agency, date, False)


'''
parsePDFtoLines
===============
Given an agency and a date, extract all the lines of the PDF,
along with a set of features for each line to use in the line classifier.
Write out a CSV file with the parsed lines and features.
'''
def parsePDFtoLines(agency, date, manual_classify):

	filepath = "docs/" + agency + "/raw_pdfs/" + agency + "_" + date + ".pdf"

	# list to hold all lines in the PDF
	lines = extractLinesFromPDF(filepath, agency, date)

	if manual_classify:
		# manually classify lines to build training set
		lines = manuallyClassifyLines(lines, agency, date)

	# convert the lines to a pandas df
	lines_df = pd.DataFrame(lines)

	# write out the lines to disk as csv
	writeDFtoCSV(lines_df, agency, date, manual_classify)



'''
extractLinesFromPDF
===================
Uses PDFPlumber to open a PDF document and convert it into a list of dicts (one per line) containing that line's text and formatting information.
Returns the list of dicts.
'''
def extractLinesFromPDF(filepath, agency, date):
	print filepath
	with pdfplumber.open(filepath) as pdf:

		# init lines list
		lines = list()

		# loop over pages
		for page_index, page in enumerate(pdf.pages):
			# crop page
			page = cropHeaderAndFooter(page, page_index)

			# convert to a list of lines with formatting
			lines += getLinesWithFormatting(page, page_index, agency, date)

		# convert font information into a set of ranked dummy vars
		lines = cleanFontNames(lines)
		lines = assignFontStyles(lines)

		# bucket left indentations into 5 ranked dummy vars
		lines = bucketLeftIndentation(lines, agency)

		return lines

def test_func(obj):
	if obj['object_type'] == "rect":
		return False
	else:
		return True

'''
cropHeaderAndFooter
===================
Crops out unwanted boilerplate at the top and bottom of each page.
Tries to determine the area to crop out using lines at the top and bottom of each page.
Returns a cropped version of the page.
'''
def cropHeaderAndFooter(page, page_index):
	'''
	find the topmost line on the page.
	if it's within the max_header_height from the top of the page,
	assume the line delineates unwanted header information,
	and use the line's location to set the header height
	'''

	header_height = 30;

	# the first page often contains a lot of extra boilerplate
	if page_index == 0:
		max_header_height = page.height / 2
	else:
		max_header_height = 200
		second_top_line_margin = 0

	topmost_line_dist_from_top = page.height

	for line in page.lines:
		line_dist_from_top = line['bottom']

		# check if the line is the topmost line found so far
		if line_dist_from_top < topmost_line_dist_from_top:
			topmost_line_dist_from_top = line_dist_from_top

			# check if the line is within the max header height
			if line_dist_from_top < max_header_height:
				header_height = line_dist_from_top

	'''
	find the bottommost line on the page.
	if it's within the max_footer_height from the bottom of the page, 
	assume the line delineates unwanted footer information,
	and use the line's location to set the footer height
	'''

	footer_height = 0 # default guestimate

	max_footer_height = 200;
	lowest_line_dist_from_bottom = page.height;

	for line in page.lines:
		line_dist_from_bottom = line['y0']

		# check if line is the lowest line found so far
		if line_dist_from_bottom < lowest_line_dist_from_bottom:
			lowest_line_dist_from_bottom = line_dist_from_bottom

			# check if the line is within the max footer height
			if line_dist_from_bottom < max_footer_height:
				footer_height = line['y1']


	crop_margins = (0, header_height, page.width, page.height-footer_height)

	return page.crop(crop_margins)



'''
getLinesWithFormatting
======================
Convert the text of a page into a list of dicts (one per line).
Each dict contains the text of that line, along with features about the formatting of the line (to use in a classifier later).
'''
def getLinesWithFormatting(page, page_index, agency, date):

	### vertical tolerance in pixels to separate lines
	y_tol = 2

	### build a list of line dicts with each line of text and important formatting
	lines = list()

	# sort list of char dicts by distance from page top
	sorted_chars = sorted(page.chars, key=itemgetter('top', 'x0'))
	# pp.pprint(sorted_chars)

	# position indicators
	current_y_pos = 0
	line_index = 0

	### get formatting for each line
	for char in sorted_chars:

		# check if this is a new line based on y position
		cur_y_min = current_y_pos - y_tol
		cur_y_max = current_y_pos + y_tol

		if cur_y_min >= char['top'] or char['top'] >= cur_y_max:

			# get all characters on that line
			lines_char_objs = [c for c in sorted_chars if c['top'] <= (char['top']+y_tol) and c['top'] >= (char['top']-y_tol)]
			lines_chars = [c['text'] for c in lines_char_objs]
			line_string = ''.join(lines_chars)

			print(line_string)

			# add line formatting to the lines_formatting list
			# assumes that all text on that line have the same formatting
			line_dict = {'agency': agency, \
				'meeting_date': date, \
				'line_id': agency + "_" + date + "_" + str(line_index), \
				'font_name': char['fontname'], \
				'font_size': char['size'], \
				'first_char': char['text'], \
				'left_inset': round(char['x0']), \
				'text': line_string}

			# if the line begins with spaces, the left_inset is thrown off.
			# to handle this, use the inset of the first non-space character.
			if lines_chars[0] == ' ':
				for c in lines_char_objs:
					if c['text'] != ' ':
						line_dict['left_inset'] = round(c['x0'])
						break

			# add additional format-based features
			line_dict = addFormattingFeatures(line_dict)

			# add to list
			lines.append(line_dict)

			# update position indicators
			current_y_pos = char['top']
			line_index += 1

	return lines



'''
addFormattingFeatures
=====================
Given a dict with a text string, add new features depending on the properties of that string.
'''
def addFormattingFeatures(line):

	# strip out whitespace
	line['text'] = line['text'].strip()
	
	# check if line is all caps
	if line['text'].isupper():
		line['uppercase'] = 1
	else:
		line['uppercase'] = 0

	# check if line starts with a number
	re_starts_num = re.compile(r'\d{1,3}\.?\s+')
	if re_starts_num.match(line['text']) is not None:
		line['starts_with_number'] = 1
	else:
		line['starts_with_number'] = 0

	# check if line starts with a sub-number (ex: 1.1)
	re_starts_subnum = re.compile(r'\d+[\.]\d+\s+')
	if re_starts_subnum.match(line['text']) is not None:
		line['starts_with_subnumber'] = 1
	else:
		line['starts_with_subnumber'] = 0

	# check if line starts with a roman numeral (ex: IV)
	re_starts_roman_numeral = re.compile(r'(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})\.\s+')
	if re_starts_roman_numeral.match(line['text']) is not None:
		line['starts_with_roman_numeral'] = 1
	else:
		line['starts_with_roman_numeral'] = 0

	# check if line starts with an enumerating letter
	re_starts_enum_letter = re.compile(r'[(]?[A-Za-z][).]?\s+')
	if re_starts_enum_letter.match(line['text']) is not None:
		line['starts_with_enum_letter'] = 1
	else:
		line['starts_with_enum_letter'] = 0

	# check if line includes a time
	re_includes_time = re.compile(r'[aA|pP].?[mM].?')
	if re_includes_time.search(line['text']) is not None:
		line['includes_time'] = 1
	else:
		line['includes_time'] = 0

	# return the expanded dict
	return line



'''
cleanFontNames
==============
Strips prefixes and foundary info from font names.
'''
def cleanFontNames(lines):
	for line in lines:
		font = line['font_name']
		if '+' in font:
			font_parts = font.split('+')
			font = font_parts[-1]
		font = re.sub(r'MT', '', font)
		line['font_name'] = font

	return lines



'''
assignFontStyles
================
Creates variables indicating if a line is set in either bold or italic type.
'''
def assignFontStyles(lines):
	for line in lines:
		if 'bold' in line['font_name'].lower():
			line['font_bold'] = 1
		else:
			line['font_bold'] = 0

		if 'italic' in line['font_name'].lower():
			line['font_italic'] = 1
		else:
			line['font_italic'] = 0

	return lines



'''
bucketLeftIndentation
=========================
Assigns the left indentation to one of six buckets.
Returns an updated list of lines.
'''
def bucketLeftIndentation(lines, agency):

	# find unique line indentations
	left_indents = list(set([line['left_inset'] for line in lines])) # intermediate conversion to a list to remove duplicates
	ranked_left_indents = sorted(left_indents)

	for line in lines:

		# add columns for each bucket
		line['indent_bucket_0'] = 0
		line['indent_bucket_1'] = 0
		line['indent_bucket_2'] = 0
		line['indent_bucket_3'] = 0
		line['indent_bucket_4'] = 0
		line['indent_bucket_5'] = 0

		if line['left_inset'] == ranked_left_indents[0]:
			line['indent_bucket_0'] = 1
		elif line['left_inset'] == ranked_left_indents[1]:
			line['indent_bucket_1'] = 1
		elif line['left_inset'] == ranked_left_indents[2]:
			line['indent_bucket_2'] = 1
		elif line['left_inset'] == ranked_left_indents[3]:
			line['indent_bucket_3'] = 1
		elif line['left_inset'] == ranked_left_indents[4]:
			line['indent_bucket_4'] = 1
		else:
			line['indent_bucket_5'] = 1

	return lines



'''
manuallyClassifyLines
=====================
Given a list of line dicts, prompt the user to classify each line. 
Return an updated dict with the classified lines.
'''
def manuallyClassifyLines(lines, agency, date):

	base_options_string = "\n 1 - Meeting Heading \n 2 - Section Heading \n 3 - Item Heading (1st line) \n 4 - Item Text \n 5 - Other \n"

	for i, line in enumerate(lines):
		print (" ")
		print(line['text'])
		score = int(raw_input("----- \nEnter class: " + base_options_string + " 6 - Undo last \n"))

		if score != 6:
			line = applyClass(line, score)
		elif score == 6:
			old_score = int(raw_input("Enter correct previous class: " + base_options_string))
			lines[i-1] = applyClass(lines[i-1], old_score)

			score = int(raw_input("Now enter correct current class: " + base_options_string))

			line = applyClass(line, score)

	return lines



'''
applyClass
==========
Given a classification integer and and line, set dummy vars for each classification.
Return the line dict.
'''
def applyClass(line, score):

	# init dummy classification vars
	line['meeting_heading'] = 0
	line['section_heading'] = 0
	line['item_heading'] = 0
	line['item_text'] = 0
	line['other_text'] = 0

	# set dummy vars based on score
	if score == 1:
		line['meeting_heading'] = 1
	elif score == 2:
		line['section_heading'] = 1
	elif score == 3:
		line['item_heading'] = 1
	elif score == 4:
		line['item_text'] = 1
	elif score == 5:
		line['other_text'] = 1

	return line


'''
writeDFtoCSV
===============
Save the full DF as a CSV to the appropriate folder.
'''
def writeDFtoCSV(df, agency, date, manual_classify):

	# select storage location based on whether this was manually classified
	if manual_classify:
		filepath = "docs/" + agency + "/training_lines/" + agency + "_" + date + "_training_lines.csv"
	else:
		filepath = "docs/" + agency + "/parsed_lines/" + agency + "_" + date + "_parsed_lines.csv"

	df.to_csv(filepath, encoding="utf-8")



if __name__ == '__main__':
    main()
