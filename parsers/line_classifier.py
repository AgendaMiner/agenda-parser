import numpy as np
import scipy
import matplotlib.pyplot as plt
from sklearn import linear_model, metrics, multiclass, cross_validation
import pandas as pd

def main():

	classifyAgendas("gavilan_ccd", ["05-10-2016"])


'''
classifyAgendas
===============
Given an agency and a list of agenda dates, classifies the lines in each agenda.
Saves the classified lines out as CSVs.
'''
def classifyAgendas(agency, dates):

	classes_list = ["meeting_heading", "section_heading", "item_heading", "item_text", "other_text"]

	# build classification model
	training_filepath = "../docs/" + agency + "/training_lines/" + agency + "_all_training_lines.csv"
	model = trainModel(training_filepath, classes_list)

	# loop through agendas for each date
	for date in dates:
		predict_filepath = "../docs/" + agency + "/parsed_lines/" + agency + "_" + date + "_parsed_lines.csv"
		classed_filepath = "../docs/" + agency + "/classed_lines/" + agency + "_" + date + "_classed_lines.csv"

		classifyLines(model, predict_filepath, classed_filepath, classes_list)


'''
trainModel
==========
Use the training file to build a model that classifies each line as
one of the inputted classes.
Returns the fitted model.
'''
def trainModel(training_filepath, classes_list):
	training_df = pd.read_csv(training_filepath, sep = ',', header = 0)
	
	# create datasets from the input file
	datasets = prepDatasets(training_df, classes_list, True)
	X_train = datasets[0]
	y_train = datasets[1]

	# train classifier
	OvR_log_cv = multiclass.OneVsRestClassifier(linear_model.LogisticRegressionCV(cv=5, penalty='l1', solver='liblinear', n_jobs=-1))
	OvR_log_cv.fit(X_train, y_train)
	log_pred_classes = OvR_log_cv.predict(X_train)
	
	print(metrics.classification_report(y_train, log_pred_classes))
	print(metrics.confusion_matrix(y_train, log_pred_classes))

	return OvR_log_cv



'''
classifyLines
=============
Given a model, an input filepath, and an output filepath, predicts
the classifications of each line in the input file, and writes out a version 
of the file with the classifications.
'''
def classifyLines(model, input_filepath, output_filepath, classes_list):

	input_df = pd.read_csv(input_filepath, sep = ',', header = 0)

	# create datasets from the input file
	datasets = prepDatasets(input_df, classes_list, False)
	X_predict = datasets[0]

	# predict classes
	preds = model.predict(X_predict)
	input_df['line_class'] = preds

	# write out predicted df to csv
	input_df.to_csv(output_filepath, index=False)



'''
prepDatasets
============
Given the path to a CSV file, convert it into an array of features, and (if y_col_name is set), to a 1-dimensional array of outcome indicators.
Return the array(s).
'''
def prepDatasets(df, y_cols, know_outcomes):

	# list of unwanted cols to drop
	cols_to_drop = ['line_id', 'meeting_date', 'text', 'font_name', 'first_char', 'font_size', 'left_inset', 'agency']
	if know_outcomes:
		cols_to_drop.extend(y_cols)

	# create feature array
	x_df = df.drop(cols_to_drop, axis=1)
	x_array = scipy.sparse.csr_matrix(x_df.values)

	# create list to return x and y arrays in
	data_arrays = [x_array]

	if know_outcomes:

		# collapse y cols
		df['line_class'] = None
		for y_col_name in y_cols:
			df.loc[(df[y_col_name]==1),'line_class'] = y_col_name

		data_arrays.append(df['line_class'])

	return data_arrays











if __name__ == '__main__':
	main()