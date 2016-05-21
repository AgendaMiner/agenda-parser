from scrapers.utils import buildDirectoryStructure
import json

def main():

	agencies_list = getAgenciesList()
	for agency in agencies_list:
		buildDirectoryStructure(agency['agency_id'], agency['agenda_type'])
	





'''
getAgenciesList
===============
Load the json list of agencies if there is one,
otherwise return an empty list.
'''
def getAgenciesList():
	agencies_list = list()
	agencies_list_filepath = "agencies_list.json"
	if os.path.exists(agencies_list_filepath):
		with open(agencies_list_filepath) as data_file:
			agencies_list = json.load(data_file)

	return agencies_list














if __name__ == '__main__':
    main()