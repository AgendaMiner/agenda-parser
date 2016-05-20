import numpy as np
import matplotlib.pyplot as plt
from sklearn import linear_model, metrics
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

	# set training file path
	training_filepath = "../docs/" + agency + "/training_lines/" + agency + "_all_training_lines.csv"

	# loop through agendas for each date
	for date in dates:
		predict_filepath = "../docs/" + agency + "/parsed_lines/" + agency + "_" + date + "_parsed_lines.csv"
		classed_filepath = "../docs/" + agency + "/classed_lines/" + agency + "_" + date + "_classed_lines.csv"

		classed_df = classifyLines(training_filepath, predict_filepath, True)
		print("classifyAgendas")
		print classed_df.columns.values.tolist()

		# classed_df.to_csv(classed_filepath, index=False)


'''
classifyLines
=============
Given a training file of classified lines and their features, 
classify the lines in an optional second file with the same features.
If a second file is not provided, tries applying the model to the training 
data and prints out evaluation metrics.
Returns the classified lines.
'''
def classifyLines(training_filepath, predict_filepath, know_outcomes):

	# read in datafiles
	training_df = pd.read_csv(training_filepath, sep = ',', header = 0)

	# list of classes
	classes_list = ["meeting_heading", "section_heading", "item_heading", "item_text", "other_text"]

	# build feature and outcome datasets
	datasets = prepDatasets(training_df, classes_list, True)
	train_X = datasets[0]

	print(train_X.shape)

	# train lasso model on each classification
	classes_models = list()
	for class_Y in datasets[1:]:
		classes_models.append(trainClassifier(train_X, class_Y))

	# load file to predict classifications on
	predict_df = pd.read_csv(predict_filepath, sep = ',', header = 0)
	predict_datasets = prepDatasets(predict_df, classes_list, know_outcomes)
	predict_X = predict_datasets[0]
	print(predict_X.shape)

	# predict each class using the lasso models
	classes_preds = list()
	for model in classes_models:
		classes_preds.append(model.predict(predict_X))

	# classify using probabilities from models
	classified_lines = classifyFromPredictions(classes_preds, classes_list)

	if know_outcomes:
		# check how well the models did at classifing the training data
		evaluateClassifications(classes_list, datasets[1:], classified_lines)
		return None
	else:
		# combine the classifications with the predict df, return the combined df
		return addLineClassesToDF(predict_df, classified_lines)


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
	x_array = np.array(x_df)

	# create list to return x and y arrays in
	data_arrays = [x_array]

	if know_outcomes:
		# create outcome arrays from y_cols
		for y_col_name in y_cols:
			data_arrays.append(df[y_col_name])

	return data_arrays



'''
trainClassifier
===============
Given arrays of features (X) and outcomes (Y), use cross-validation 
to set the lasso penalty and train a lasso regression model.
Return the trained model.
'''
def trainClassifier(train_X, train_Y):
	lasso_cv = linear_model.LassoCV(cv = 10, verbose = False)
	lasso_cv.fit(train_X,train_Y)

	return lasso_cv


'''
classifyFromPredictions
=======================
Given a list of classes and a list of lists of predicted probabilities 
that a line belongs to a certain class, assign the line to the class with
the highest predicted probability.
Return a list of classified lines.
'''
def classifyFromPredictions(pred_probs_by_class, classes_list):

	# build list of class dicts
	classified_lines = list()

	# loop over each line
	for i in range(len(pred_probs_by_class[0])):

		# build a list of predicted probabilities for each classification
		prob_scores = list()
		for j in range(len(classes_list)):
			prob_scores.append(pred_probs_by_class[j][i])
			
		# extract the highest score
		highest_score = max(prob_scores)

		# classify the line as the class with the highest prob score
		line_class = None
		for i, class_name in enumerate(classes_list):
			if prob_scores[i] == highest_score:
				line_class = class_name

		classified_lines.append(line_class)

	return classified_lines

'''
evaluateClassifications
=======================
Given a list of predicted classifications, a list of classes, and a list of lists of binary indicators of whether each line actually belongs to class, calculate the accuracy, precision, and recall of the classifier.
'''
def evaluateClassifications(classes_list, true_classes_list_of_lists, pred_y):

	# convert the list of lists of true class indicators 
	# into a single list of true classes
	true_y = convertListOfBinaryListsToList(true_classes_list_of_lists, classes_list)

	# calc accuracy
	print("Accuracy:")
	print(metrics.accuracy_score(true_y, pred_y))

	# calc precision and recall
	more_metrics = metrics.precision_recall_fscore_support(true_y, pred_y)
	print("Precision:")
	print(more_metrics[0])
	print("Recall:")
	print(more_metrics[1])
	

'''
convertListOfBinaryListsToList
==============================
Given a list of lists of exclusive binary dummy vars,
and a list of the dummy variables, build a single list of the dummy var assigned to each entry
'''
def convertListOfBinaryListsToList(list_of_lists, colnames):
	single_list = list()

	for i in range(len(list_of_lists[0])):
		var_name = None
		for j in range(len(list_of_lists)):
			if list_of_lists[j][i] == 1:
				var_name = colnames[j]

		if var_name is None:
			for k in range(len(list_of_lists)):
				print("ERROR ON LINE " + str(i))
				print(list_of_lists[k][i])
		single_list.append(var_name)

	return single_list


'''
addLineClassesToDF
=========================
Convert the classified lines list to a numpy array and add it to the DF.
Return the updated DF.
'''
def addLineClassesToDF(df, classified_lines):

	# convert classified lines to numpy array
	lines_array = np.asarray(classified_lines)

	# add array to df
	df["line_class"] = lines_array

	print("addLineClassesToDF")
	print df.columns.values.tolist()

	return df












if __name__ == '__main__':
	main()