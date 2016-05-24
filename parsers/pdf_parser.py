import re
import csv
import os.path
import pickle
import pandas as pd
import pdfplumber
from operator import itemgetter
from collections import Counter
from sklearn.feature_extraction.text import CountVectorizer



def main():

	agency = "cupertino_usd"
	date = "04-05-2016"

	parsePDFtoLines(agency, date, True)


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
		lines = generalizeFontInfo(lines, agency)

		# convert left indentation into a set of ranked dummy vars
		lines = generalizeLeftIndentation(lines, agency)

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

	return lines



'''
addFormattingFeatures
=====================
Given a dict with a text string, add new features depending on the properties of that string.
'''
def addFormattingFeatures(line):

	# count how many spaces are at the start of the line
	line['leading_spaces'] = len(line['text']) - len(line['text'].lstrip(' '))

	# strip out whitespace
	line['text'] = line['text'].strip()
	
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
generalizeFontInfo
==================
Converts the raw font and font-size information from PDFPlumber into a set of relative categories.
Returns an updated list of line dicts.
'''
def generalizeFontInfo(lines, agency):

	### font-face frequencies
	lines = assignFontFrequencies(lines, agency)

	### font sizes
	lines = assignFontSizes(lines, agency)

	return lines



'''
assignFontFrequencies
=====================
Checks to see if a list of ranked fonts has already been created, 
otherwise orders the unique font-faces by frequency, then creates a set of dummy variables
for each frequency (set to 1 if the font-face for that line, 0 otherwise)
Returns an updated list of line dicts
'''
def assignFontFrequencies(lines, agency):

	ranked_fonts_filepath = "docs/" + agency + "/data/ranked_fonts.p"
	
	if os.path.exists(ranked_fonts_filepath):
		ranked_fonts = pickle.load(open(ranked_fonts_filepath, "rb" ))

	else:
		# find unique fonts
		all_fonts = [line['font_name'] for line in lines]
		font_counter = Counter(all_fonts)
		ranked_font_tuples = font_counter.most_common()
		ranked_fonts = [font_tuple[0] for font_tuple in ranked_font_tuples]
		pickle.dump(ranked_fonts, open(ranked_fonts_filepath, "wb"))

	# create font_freq features for each line
	return assignRankedDummyVars(lines, ranked_fonts, 'font_freq_', 'font_name')



'''
assignFontSizes
=====================
Checks if a set of unique font-sizes already exists, 
otherwise orders the unique font-sizes in descending order, 
then creates a set of ranked dummy variables (set to 1 if the font-size for that line, 0 otherwise).
Returns an updated list of line dicts
'''
def assignFontSizes(lines, agency):

	ranked_font_sizes_filepath = "docs/" + agency + "/data/ranked_font_sizes.p"
	
	if os.path.exists(ranked_font_sizes_filepath):
		ranked_font_sizes = pickle.load(open(ranked_font_sizes_filepath, "rb" ))

	else:
		# find unique font sizes
		font_sizes = list(set([line['font_size'] for line in lines])) # intermediate conversion to a set to remove duplicates
		ranked_font_sizes = sorted(font_sizes, reverse=True)
		pickle.dump(ranked_font_sizes, open(ranked_font_sizes_filepath, "wb"))

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
Checks if a list of indentations from the left side of the page already exists,
otherwise creates a set of dummy variables ranking how indented the left side of the line is.
Returns an updated list of lines.
'''
def generalizeLeftIndentation(lines, agency):

	ranked_left_indents_filepath = "docs/" + agency + "/data/ranked_left_indents.p"
	
	if os.path.exists(ranked_left_indents_filepath):
		ranked_left_indents = pickle.load(open(ranked_left_indents_filepath, "rb" ))

	else:
		# find unique line indentations
		left_indents = list(set([line['left_inset'] for line in lines])) # intermediate conversion to a list to remove duplicates
		ranked_left_indents = sorted(left_indents)
		pickle.dump(ranked_left_indents, open(ranked_left_indents_filepath, "wb"))

	# create left_indent features for each line
	return assignRankedDummyVars(lines, ranked_left_indents, 'left_indent_', 'left_inset')




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
