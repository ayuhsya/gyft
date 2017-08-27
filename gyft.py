import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
from bs4 import BeautifulSoup as bs
import re
import json
import getpass
import constants


# Parsing from commmand line
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-u", "--user", help="ERP Username/Login ID")
args = parser.parse_args()
erp_password = getpass.getpass("Enter your ERP password: ")
# Parsing ends


session = requests.Session()
res = session.get(constants.ERP_HOMEPAGE_URL)
soup = bs(res.text, 'html.parser')
sessionToken = soup.find_all(id='sessionToken')[0].attrs['value']

res = session.post(constants.ERP_SECRET_QUESTION_URL, data={'user_id': args.user},
           headers = constants.headers)
secret_question = res.text
print (secret_question)
secret_answer = getpass.getpass("Enter the answer to the security question: ")
login_details = {
    'user_id': args.user,
    'password': erp_password,
    'answer': secret_answer,
    'sessionToken': sessionToken,
    'requestedUrl': 'https://erp.iitkgp.ernet.in/IIT_ERP3',
}
res = session.post(constants.ERP_LOGIN_URL, data=login_details,
           headers = constants.headers)
ssoToken = re.search(r'\?ssoToken=(.+)$',
                     res.history[1].headers['Location']).group(1)

timetable_details = {
    'ssoToken': ssoToken,
    'module_id': '16',
    'menu_id': '40',
}

# This is just a hack to get cookies. TODO: do the standard thing here
abc = session.post('https://erp.iitkgp.ernet.in/Acad/student/view_stud_time_table.jsp', headers=constants.headers, data=timetable_details)
cookie_val = None
for entry in session.cookies:
    if (entry.path == "/Acad/"):
        cookie_val = entry.value

cookie = {
    'JSESSIONID': cookie_val,
}
res = session.post('https://erp.iitkgp.ernet.in/Acad/student/view_stud_time_table.jsp',cookies = cookie, headers=constants.headers, data=timetable_details)

soup = bs(res.text, 'html.parser')
rows_head = soup.findAll('table')[2]
rows = rows_head.findAll('tr')
times = []

for a in rows[0].findAll('td'):
    if ('AM' in a.text or 'PM' in a.text):
        times.append(a.text)

timetable_dict = {}


for i in range(1, len(rows)):
    timetable_dict[constants.days[i]] = {}
    tds = rows[i].findAll('td')
    print(tds)
    time = 0
    for a in range(1, len(tds)):
    	if tds[a].find('b'):
        	txt = tds[a].find('b').text.strip()
        print (txt)
        if (len(txt) >= 7):
        	if tds[a].find('b'):
        		timetable_dict[constants.days[i]][times[time]] = list((tds[a].find('b').text[:7],tds[a].find('b').text[7:], int(tds[a]._attr_value_as_string('colspan'))))
        	else:
        		timetable_dict[constants.days[i]][times[time]] = list()
        print (timetable_dict)


    	if tds[a]._attr_value_as_string('colspan'):
        	time = time + int(tds[a]._attr_value_as_string('colspan'))
        else:
        	time = time + 1


def merge_slots(in_dict):
    for a in in_dict:
        in_dict[a] = sorted(in_dict[a])
        for i in range(len(in_dict[a]) - 1, 0, -1):
            if (in_dict[a][i][0] == in_dict[a][i-1][0] + in_dict[a][i-1][1]):
                in_dict[a][i-1][1] = in_dict[a][i][1] + in_dict[a][i-1][1]
                in_dict[a].remove(in_dict[a][i])
        in_dict[a] = in_dict[a][0]
    return (in_dict)


for day in timetable_dict.keys():
    subject_timings = {}
    for time in timetable_dict[day]:
        flattened_time = int(time[:time.find(':')])
        if (flattened_time < 6):
            flattened_time += 12
        if (not timetable_dict[day][time][0] in subject_timings.keys()):
            subject_timings[timetable_dict[day][time][0]] = []
        subject_timings[timetable_dict[day][time][0]].append([flattened_time, timetable_dict[day][time][2]])
    subject_timings = merge_slots(subject_timings)
    for time in list(timetable_dict[day].keys()):
        flattened_time = int(time[:time.find(':')])
        if (flattened_time < 6):
            flattened_time += 12
        if (not flattened_time == subject_timings[timetable_dict[day][time][0]][0]):
            del (timetable_dict[day][time])
        else:
            timetable_dict[day][time][2] = subject_timings[timetable_dict[day][time][0]][1]


with open('data.txt', 'w') as outfile:
    json.dump(timetable_dict, outfile, indent = 4, ensure_ascii=False)

print ("\n\nTimetable saved to data.txt file. Be sure to edit this file to have desired names of subjects rather than subject codes.\n")
