import pdfplumber
from operator import itemgetter
import re
from collections import Counter
from sklearn.feature_extraction.text import CountVectorizer
import csv


def main():

	agency = "sunnyvale"
	date = "4-19-16"

	parsePDFtoLines(agency, date, False)

	# create a DTM from the line text
	# dtm = buildDTM(lines)


'''
'''
def parsePDFtoLines(agency, date, manual_classify):

	# list to hold all lines in the PDF
	lines = extractLinesFromPDF("../docs/" + agency + "/raw_pdfs/" + agency + "_" + date + ".pdf", agency, date)

	if manual_classify:
		# manually classify lines to build training set
		lines = manuallyClassifyLines(lines, agency, date)

	# write out the lines to disk as csv
	writeLinesToCSV(lines, agency, date, manual_classify)


'''
extractLinesFromPDF
===================
Uses PDFPlumber to open a PDF document and convert it into a list of dicts (one per line) containing that line's text and formatting information.
Returns the list of dicts.
'''
def extractLinesFromPDF(filepath, agency, date):
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
		lines = generalizeFontInfo(lines)

		# convert left indentation into a set of ranked dummy vars
		lines = generalizeLeftIndentation(lines)

		return lines


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

	header_height = 100;

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

	footer_height = 100 # default guestimate

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

	### convert the page into a list of lines of text
	y_tol = 2
	all_text = page.extract_text(x_tolerance=2, y_tolerance=y_tol)
	text_lines = all_text.splitlines()

	### build a list of line dicts with each line of text and important formatting
	lines = list()

	# sort list of char dicts by distance from page top
	sorted_chars = sorted(page.chars, key=itemgetter('top', 'x0')) 

	# position indicators
	current_y_pos = 0
	line_index = 0

	### get formatting for each line
	for char in sorted_chars:

		# check if this is a new line based on y position
		cur_y_min = current_y_pos - y_tol
		cur_y_max = current_y_pos + y_tol

		if cur_y_min >= char['top'] or char['top'] >= cur_y_max:

			# sanity check that the first character is the same as the first character in the text_lines string, warn if not (SEEMS TO HAVE A BUG WITH NUMBERS)
			if char['text'] != text_lines[line_index][:1]:
				print( "MISMATCH ON PAGE " + str(page_index) + ", LINE " + str(line_index))
				print("--FIRST CHAR: " + char['text'] + ", TEXT: " + text_lines[line_index])
				
			# add line formatting to the lines_formatting list
			# assumes that all text on that line have the same formatting
			line_dict = {'agency': agency, \
				'meeting_date': date, \
				'line_id': agency + "_" + date + "_" + str(line_index), \
				'font_name': char['fontname'], \
				'font_size': char['size'], \
				'first_char': char['text'], \
				'left_inset': char['x0'], \
				'text': text_lines[line_index]}

			# add additional format-based features
			line_dict = addFormattingFeatures(line_dict)

			# add to list
			lines.append(line_dict)

			# update position indicators
			current_y_pos = char['top']
			line_index += 1

	# for line in lines:
	# 	print line['left_inset']
	# 	print line['text']

	# print len(lines)

	return lines



'''
addFormattingFeatures
=====================
Given a dict with a text string, add new features depending on the properties of that string.
'''
def addFormattingFeatures(line):
	
	# check if line is all caps
	if line['text'].isupper():
		line['uppercase'] = 1
	else:
		line['uppercase'] = 0

	# check if line starts with a number
	re_starts_num = re.compile(r'\d+\.?\s+')
	if re_starts_num.match(line['text']) is not None:
		line['starts_with_number'] = 1
	else:
		line['starts_with_number'] = 0

	# check if line includes a time
	re_includes_time = re.compile(r'[aA|pP].?M.?')
	if re_includes_time.search(line['text']) is not None:
		line['includes_time'] = 1
	else:
		line['includes_time'] = 0

	# return the expanded dict
	return line



'''
generalizeFontInfo
==================
Converts the raw font and font-size information from PDFPlumber into a set of relative categories.
Returns an updated list of line dicts.
'''
def generalizeFontInfo(lines):

	### font-face frequencies
	lines = assignFontFrequencies(lines)

	### font sizes
	lines = assignFontSizes(lines)

	return lines



'''
assignFontFrequencies
=====================
Orders the unique font-faces by frequency, then creates a set of dummy variables
for each frequency (set to 1 if the font-face for that line, 0 otherwise)
Returns an updated list of line dicts
'''
def assignFontFrequencies(lines):

	# find unique fonts
	all_fonts = [line['font_name'] for line in lines]
	font_counter = Counter(all_fonts)
	ranked_font_tuples = font_counter.most_common()
	ranked_fonts = [font_tuple[0] for font_tuple in ranked_font_tuples]

	# create font_freq features for each line
	return assignRankedDummyVars(lines, ranked_fonts, 'font_freq_', 'font_name')



'''
assignFontSizes
=====================
Orders the unique font-sizes in descending order, then creates a set of ranked dummy variables (set to 1 if the font-size for that line, 0 otherwise).
Returns an updated list of line dicts
'''
def assignFontSizes(lines):

	# find unique font sizes
	font_sizes = list(set([line['font_size'] for line in lines])) # intermediate conversion to a list to remove duplicates
	ranked_font_sizes = sorted(font_sizes, reverse=True)
	# print ranked_font_sizes

	# create font_size features for each line
	return assignRankedDummyVars(lines, ranked_font_sizes, 'font_size_', 'font_size')



'''
assignRankedDummyVars
=====================
Creates a set of dummy variables by checking which option in a list of ranked options matches the attribute of each line (1 if match, 0 otherwise).
Returns an updated list of lines.
'''
def assignRankedDummyVars(lines, ranked_vars, dummy_basename, line_attribute):
	for line in lines:
		for i, ranked_attr in enumerate(ranked_vars):
			key = dummy_basename + str(i)

			# check if the line attribute matches the active ranked attr
			if line[line_attribute] == ranked_attr:
				line[key] = 1
			else:
				line[key] = 0

	return lines



'''
generalizeLeftIndentation
=========================
Creates a set of dummy variables ranking how indented the left side of the line is.
Returns an updated list of lines.
'''
def generalizeLeftIndentation(lines):

	# find unique line indentations
	left_indents = list(set([line['left_inset'] for line in lines])) # intermediate conversion to a list to remove duplicates
	ranked_left_indents = sorted(left_indents)

	# create left_indent features for each line
	return assignRankedDummyVars(lines, ranked_left_indents, 'left_indent_', 'left_inset')



'''
manuallyClassifyLines
=====================
Given a list of line dicts, prompt the user to classify each line. 
Store the classified lines in an updated dict, save this dict to disk, and return it.
'''
def manuallyClassifyLines(lines, agency, date):

	for i, line in enumerate(lines):
		print (" ")
		print(line['text'])
		score = int(raw_input("----- \nEnter class: \n 1 - Meeting Heading \n 2 - Section Heading \n 3 - Item Heading \n 4 - Item Text \n 5 - Other \n 6 - Undo last \n"))

		if score != 6:
			line = applyClass(line, score)
		elif score == 6:
			old_score = int(raw_input("Enter correct previous class: \n 1 - Meeting Heading \n 2 - Section Heading \n 3 - Item Heading \n 4 - Item Text \n 5 - Other \n"))
			lines[i-1] = applyClass(lines[i-1], old_score)

			score = int(raw_input("Now enter correct current class: \n 1 - Meeting Heading \n 2 - Section Heading \n 3 - Item Heading \n 4 - Item Text \n 5 - Other \n"))

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
writeLinesToCSV
===============
Save the lines as a CSV to the appropriate folder.
'''
def writeLinesToCSV(lines, agency, date, manual_classify):

	# select storage location based on whether this was manually classified
	if manual_classify:
		filename = "../docs/" + agency + "/training_lines/" + agency + "_" + date + "_training_lines.csv"
	else:
		filename = "../docs/" + agency + "/parsed_lines/" + agency + "_" + date + "_parsed_lines.csv"

	with open(filename, 'w') as csvfile:
	    fieldnames = lines[0].keys()

	    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
	    writer.writeheader()

	    for line in lines:
	    	writer.writerow(dict((k, v.encode('utf-8') if type(v) is unicode else v) for k, v in line.iteritems()))



'''
buildDTM
========
Use Scikit-learn to build a document-term matrix from the text of the lines
'''
def buildDTM(lines):
	text_lines = [line['text'] for line in lines]

	vectorizer = CountVectorizer(min_df=1)
	dtm = vectorizer.fit_transform(text_lines)
	print dtm


if __name__ == '__main__':
    main()
