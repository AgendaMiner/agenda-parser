import numpy as np
import pprint
import scipy
import os
import matplotlib.pyplot as plt
from sklearn import linear_model, svm, metrics, multiclass, cross_validation, preprocessing, grid_search, feature_extraction
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
import pandas as pd

pp = pprint.PrettyPrinter(indent=4)

def main():

	classifyAgendas("cupertino_usd", ["04-05-2016"], True)


'''
classifyAgendas
===============
Given an agency and a list of agenda dates, classifies the lines in each agenda.
Saves the classified lines out as CSVs.
'''
def classifyAgendas(agency, dates, eval_model):

	classes_list = ["meeting_heading", "section_heading", "item_heading", "item_text", "other_text"]

	# build classification model
	training_directory = "docs/" + agency + "/training_lines/"
	model_pieces = trainModel(training_directory, classes_list, eval_model)

	# loop through agendas for each date
	for date in dates:
		predict_filepath = "docs/" + agency + "/parsed_lines/" + agency + "_" + date + "_parsed_lines.csv"
		classed_filepath = "docs/" + agency + "/classed_lines/" + agency + "_" + date + "_classed_lines.csv"

		print(predict_filepath)

		classifyLines(model_pieces, predict_filepath, classed_filepath, classes_list)


'''
trainModel
==========
Use the training file to build a model that classifies each line as
one of the inputted classes.
Returns the fitted model.
'''
def trainModel(training_directory, classes_list, eval_model):
	training_df = buildTrainingDataset(training_directory)

	# create a DTM vectorizer and dummy encoder object for use later
	model_pieces = dict()
	model_pieces['vect'] = CountVectorizer(strip_accents="ascii", ngram_range=(1,3), stop_words='english', max_df=0.9, min_df=2, binary=True)
	model_pieces['encoder'] = feature_extraction.DictVectorizer(sparse=False)
	
	# create datasets from the input file
	datasets, model_pieces = prepDatasets(model_pieces, training_df, classes_list, True)
	X = datasets[0]
	y = datasets[1]

	# create interaction features
	# interactor = preprocessing.PolynomialFeatures(interaction_only=True)
	# x = interactor.fit_transform(x)

	# split into training and validation sets if eval_model is True
	if eval_model:
		X_train, X_test, y_train, y_test = cross_validation.train_test_split(X, y, test_size=0.33, stratify=y)
	else:
		X_train = X
		y_train = y

	## LOG REGRESSION

	# train classifier
	model_pieces['model'] = multiclass.OneVsRestClassifier(linear_model.LogisticRegressionCV(cv=5, penalty='l1', solver='liblinear', n_jobs=-1))
	model_pieces['model'].fit(X_train, y_train)

	if eval_model:
		log_pred_classes = model_pieces['model'].predict(X_test)
		print(model_pieces['model'].coef_)
	
		print(metrics.classification_report(y_test, log_pred_classes))
		print(metrics.confusion_matrix(y_test, log_pred_classes))

	## SVM - LOGISTIC REGRESSION WORKS BETTER
	# # train classifier
	# # raw_svm = svm.SVC(decision_function_shape='ovr', class_weight='balanced')
	# # search_params = {'kernel':['rbf'], 'C':[1, 10, 100, 1000, 10000, 100000, 1000000], 'gamma': [0.00001, 0.0001, 0.01, 1, 10, 100]}
	# # svm_cv = grid_search.GridSearchCV(raw_svm, param_grid=search_params, cv=5, n_jobs=-1, verbose=5)
	# # svm_cv.fit(X_train, y_train)
	# # print(svm_cv.best_params_)
	# svm_classifier = svm.SVC(decision_function_shape='ovr', class_weight='balanced', kernel='rbf', C=100000, gamma=0.00001)
	# svm_classifier.fit(X_train, y_train)

	# if eval_model:
	# 	pred_classes = svm_classifier.predict(X_test)
	
	# 	print(metrics.classification_report(y_test, pred_classes))
	# 	print(metrics.confusion_matrix(y_test, pred_classes))

	return model_pieces



'''
buildTrainingDataset
======================
Given a directory path, load all the csv files in that directory as pandas
dataframes, and merge them together.
'''
def buildTrainingDataset(directory_path):
	df_list = list()
	for filename in os.listdir(directory_path):
		if filename.endswith(".csv"):
			filepath = os.path.join(directory_path, filename)
			df = pd.read_csv(open(filepath,'rU'), sep = ',', header = 0)
			df_list.append(df)

	return pd.concat(df_list, ignore_index=True) 



'''
classifyLines
=============
Given a model, an input filepath, and an output filepath, predicts
the classifications of each line in the input file, and writes out a version 
of the file with the classifications.
'''
def classifyLines(model_pieces, input_filepath, output_filepath, classes_list):

	input_df = pd.read_csv(input_filepath, sep = ',', header = 0)

	# create datasets from the input file
	datasets, model_pieces = prepDatasets(model_pieces, input_df, classes_list, False)
	X_predict = datasets[0]

	# predict classes
	preds = model_pieces['model'].predict(X_predict)
	input_df['line_class'] = preds

	# write out predicted df to csv
	input_df.to_csv(output_filepath, index=False)



'''
prepDatasets
============
Given the path to a CSV file, convert it into an array of features, and (if y_col_name is set), to a 1-dimensional array of outcome indicators. Use the given vectorizer to create a DTM from the text.
Return the array(s).
'''
def prepDatasets(model_pieces, df, y_cols, know_outcomes):

	# list of unwanted cols to drop
	cols_to_drop = ['line_id', 'meeting_date', 'text', 'font_name', 'first_char', 'font_size', 'left_inset', 'agency']
	if know_outcomes:
		cols_to_drop.extend(y_cols)

	# create feature array
	x_df = df.drop(cols_to_drop, axis=1)
	x_array = x_df.values

	# create dummy variables for categorical features
	feature_dummies, model_pieces = convertFeaturesToDummyVariables(df, model_pieces, know_outcomes)
	x_array = np.concatenate((x_array, feature_dummies), axis=1)

	# create document-term matrix
	df['text'].fillna('', inplace=True)
	if know_outcomes:
		counts_matrix = model_pieces['vect'].fit_transform(df['text'])
	else:
		counts_matrix = model_pieces['vect'].transform(df['text'])

	# merge DTM with feature array
	x_array = np.concatenate((x_array, counts_matrix.toarray()), axis=1)

	# create list to return x and y arrays in
	data_arrays = [x_array]

	if know_outcomes:

		# collapse y cols
		df['line_class'] = None
		for y_col_name in y_cols:
			df.loc[(df[y_col_name]==1),'line_class'] = y_col_name

		data_arrays.append(df['line_class'])

	return [data_arrays, model_pieces]



'''
convertFeaturesToDummyVariables
===============================
Converts categorical features to dummy variables.
'''
def convertFeaturesToDummyVariables(df, model_pieces, know_outcomes):

	# convert numeric (but really categorical) variables to strings
	df['font_size'] = df['font_size'].astype(str)
	df['left_inset'] = df['left_inset'].astype(str)

	# create dict from categorical columns
	cols_to_create_dummies = ['font_name', 'font_size', 'left_inset']
	to_dummies_dict = df[cols_to_create_dummies].to_dict(orient='records')

	# encode variables
	if know_outcomes:
		dummies_array = model_pieces['encoder'].fit_transform(to_dummies_dict)
	else:
		dummies_array = model_pieces['encoder'].transform(to_dummies_dict)

	return [dummies_array, model_pieces]










if __name__ == '__main__':
	main()