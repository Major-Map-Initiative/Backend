from bs4 import BeautifulSoup
import json
import requests
import pandas as pd
import numpy as np
import re #regex
import networkx as nx
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from utils.tools import replace_all, extract_course_catalog




#department IDs for the course catalog pages, data structs are a set btw
department = {'ANTH','BIOI','BIOL','CHEM','CHIN','CLAS','CCS','COGS','COMM','CGS','CAT','DSC','DSGN','DOC','ECON','EDS','ENG','BENG','CSE','ECE','MAE','NANO','SE','ENVR','ESYS','ETHN','FMPH','FILM','GLBH','HIST','HDS','HR','HUM','INTL','JAPN','JWSP','LATI','LAWS','LING','LIT','MGT','MATH','MUS','PHIL','PHYS','POLI','PSYC','RELI','SCIS','SIO','SOC','THEA','TWS','USP','VIS'}

#These preface department course numberings, since deparments sometimes have multiple ID's within (e.g. biology)
dept_id = {'ANTH','BIOI','BIOL', 'BILD', 'BIBC', 'BICD', 'BIEB', 'BIMM', 'BIPN', 'BISP', 'CHEM','CHIN','CLAS','CCS','COGS','COMM','CGS','CAT','DSC','DSGN','DOC','ECON','EDS','ENG','BENG','CSE','ECE','MAE','NANO','SE','ENVR','ESYS','ETHN','FMPH','FILM','GLBH','HIST','HDS','HDP','HR','HUM','INTL','JAPN','JWSP','LATI','LAWS','LING','LIT','MGT','MATH','MUS','PHIL','PHYS','POLI','PSYC','RELI','SCIS','SIO','SOC','THEA','TWS','USP','VIS'}




for dept in department:
    names, descriptions = extract_course_catalog(dept) #descriptions include prereqs
    df = pd.DataFrame(columns=['Course Name', 'Course Description', 'Course Units']) #Pandas not part of current pipeline but may be useful later
    courses = {}

    for course, description in zip(names, descriptions):
        course, description = course.getText(), description.getText() #Extract text from beautifulsoup objects

        course_id = course[course.index(' ')+1:course.index('.')] # Getting course ID to filter out grad courses later.

        course_name_verbose = course[course.index('.')+2:course.index('(')-1] #Extracting course name (without ID)

        #Non course prerequisites to append to end of description
        if "consent" in description.lower().split(): #consent of instructor
            consent_flag = True
        else:
            consent_flag = False

        if any(word in ["ap", "placement", "sat"] for word in description.lower().split()): #placement exam keywords
            exam_flag = True
        else:
            exam_flag = False

        if "standing" in description.lower().split():  # as in 'upper-division standing'
            standing_flag = True
        else:
            standing_flag = False

        if "approval" in description.lower().split():  # as in department approval required
            approval_flag = True
        else:
            approval_flag = False

        # Course description w/o preqrequisites or other sections
        try:
            if description.index("Prerequisites:"):
                course_desc_verbose = description[:description.index("Prerequisites:")]
            else: #for other text
                course_desc_verbose = description[:description.index("Note:")]
        except ValueError:
            course_desc_verbose = description

        while course_id[-1].isalpha() or course_id[-1] == '-':
            course_id = course_id[:-1]

        #Adding those non course prereqs at the end of the description:
        if consent_flag:
            course_desc_verbose = course_desc_verbose + " ** Consent of instructor to enroll possible  **"
        if exam_flag:
            course_desc_verbose = course_desc_verbose + " ** Exam placement options to enroll possible ** "
        if standing_flag:
            course_desc_verbose = course_desc_verbose + " ** Upper-division standing required ** "
        if approval_flag:
            course_desc_verbose = course_desc_verbose + " ** Department approval required ** "


        course_id = int(re.findall(r'\d+', course_id)[0]) #using regex (an alternative method from the previous ones)
        if course_id >= 200: #filter grad courses
            continue

        # Grabs course info.
        course = course.replace(":",".") #normalizing character after the number
        course_name = course[:course.index('.')]
        cleaned = [] #array for cleaned prerequisites
        if "Prerequisites:" in description:
            prereqs = description.split("Prerequisites:",1)[1]
            for i, char in enumerate(prereqs):
                if char == "." or char ==";": #?
                    prereqs = prereqs[:i]

            prereqs_list = prereqs.split(" ") #Turning prereqs into a list of all of its words for parsing

            encounter =False #Set true when encountering a new course in the listed prerequisites

            prereqs_list = [x for x in prereqs_list if x != ''] #removing spaces/blank characters
            for i, word in enumerate(prereqs_list):
                word = replace_all([',',')','\n','\t'], word) #replacing buggy characters
                if word in dept_id:
                    cleaned.append(word + " "+ replace_all([',',')','\n','\t'], prereqs_list[i+1]))
                    encounter = True
                elif word == "or" and encounter:
                    if prereqs_list[i+1] in dept_id:
                        cleaned.append('or')
                    encounter = False
                elif word == "and":
                    cleaned.append('and')
                    if len(cleaned) == 1:
                        cleaned.remove("and")

            if len(cleaned) >0 and cleaned[-1] == 'or':
                cleaned.pop()

        #courses[course_name] = cleaned #old version

        #creating dictionary with desired data for frontend
        courses[course_name] = {"prerequisites":cleaned, "name": course_name_verbose, "description": course_desc_verbose}

        #creating individual json for current deparment
        with open('./json/'+dept+'.json','w') as fp:
            json.dump(courses,fp,indent=4)

        #Non-pipeline vars for Pandas
        course_title = course[course.index('.')+1:course.index('(')-1]
        course_units = course[course.index('('):course.index(')')+1]

        #For potential pandas use (not in pipeline): append row to data frame.
        df = df.append({
            'Course Name': course_name,
            'Course Description': description,
            'Course Units': course_units,
            'Prereqs': cleaned
        }, ignore_index=True)



#merging all saved jsons into a master json for website
master_dict = {}
for dept in department:
    print(dept)
    try:
        dept_dict = json.load(open('./json/' + dept + '.json'))
        master_dict.update(dept_dict)
    except FileNotFoundError:
        print('bad: ', dept)

with open('./json/master_prereqs.json','w') as fp:
    json.dump(master_dict,fp,indent=4)
