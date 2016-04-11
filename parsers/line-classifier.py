import numpy as np
import matplotlib.pyplot as plt
from sklearn import linear_model, metrics
import pandas as pd

#### temp workspace for Ipython repl

# df = pd.read_csv('sunnyvale_4-12-16_lines_classified.csv', sep = ',', header = 0)

# # subset to X (independent features)
# x_df = df.drop(['meeting_heading', 'section_heading', 'item_heading', 'item_text', 'other_text', 'line_id', 'meeting_date', 'text', 'font_name', 'first_char', 'font_size', 'left_inset', 'agency'], axis=1)

# # subset to Y indicators for each line type
# meeting_heading_df = df[['meeting_heading']]
# section_heading_df = df['section_heading']
# item_heading_df = df[['item_heading']]
# item_text_df = df[['item_text']]
# other_text_df = df[['other_text']]

# # convert to numpy arrays
# X = np.array(x_df)
# y = np.array(section_heading_df)






def main():

	# list of classes
	classes_list = ["meeting_heading", "section_heading", "item_heading", "item_text", "other_text"]

	# build feature and outcome datasets
	datasets = prepDatasets("sunnyvale_4-12-16_lines_classified.csv", classes_list)
	train_X = datasets[0]

	# train lasso model on each classification
	classes_models = list()
	for class_Y in datasets[1:]:
		classes_models.append(trainClassifier(train_X, class_Y))

	# TODO - GET TESTING DATASET HERE

	# predict each class using the lasso models
	classes_preds = list()
	for model in classes_models:
		classes_preds.append(model.predict(train_X))

	# classify using probabilities from models
	lines_pred_classes = classifyFromPredictions(classes_preds)

	# classifications = list()
	# for pred in raw_predicts:
	# 	pred_class = 0
	# 	if pred > 0.5:
	# 		pred_class = 1

	# 	classifications.append(pred_class)


	# # check model accuracy
	# eval_metrics = metrics.precision_recall_fscore_support(y_true = train_Y, y_pred = classifications, average='micro')

	# print eval_metrics



'''
prepDatasets
============
Given the path to a CSV file, convert it into an array of features, and (if y_col_name is set), to a 1-dimensional array of outcome indicators.
Return the array(s)
'''
def prepDatasets(datafile, y_cols):

	# read in datafile
	df = pd.read_csv(datafile, sep = ',', header = 0)

	# list of unwanted cols to drop
	cols_to_drop = y_cols.extend(['line_id', 'meeting_date', 'text', 'font_name', 'first_char', 'font_size', 'left_inset', 'agency'])

	# create feature array
	x_df = df.drop(cols_to_drop, axis=1)
	x_array = np.array(x_df)

	# create list to return x and y arrays in
	data_arrays = [x_array]

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
ADD THIS
'''
def classifyFromPredictions(pred_probs_by_class):
	















if __name__ == '__main__':
	main()