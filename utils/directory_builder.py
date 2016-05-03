import os
 
def main():
	agency = "scc_boe"
 	agenda_type = "boarddocs"
 	buildDirectoryStructure(agency, agenda_type)


'''
buildDirectoryStructure
=======================
Given a shorthand name for an agency and the type of agenda 
it uses, create the necessary subdirectories within the docs folder.
'''
def buildDirectoryStructure(agency, agenda_type):

	# create base directory
	base_dir = "../docs/%s" % agency
	if not os.path.exists(base_dir):
		os.makedirs(base_dir)

	# create structured agendas subdirectory
	agendas_dir = base_dir + "/structured_agendas"
	if not os.path.exists(agendas_dir):
		os.makedirs(agendas_dir)

	# create additional directories if agenda type is pdf
	if agenda_type == "pdf":

		pdf_dirs = list()
		pdf_dirs.append(base_dir + "/data")
		pdf_dirs.append(base_dir + "/classed_lines")
		pdf_dirs.append(base_dir + "/parsed_lines")
		pdf_dirs.append(base_dir + "/raw_pdfs")
		pdf_dirs.append(base_dir + "/training_lines")
		
		for dir in pdf_dirs:
			if not os.path.exists(dir):
				os.makedirs(dir)




 	










if __name__ == '__main__':
	main()