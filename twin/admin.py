from django.contrib import admin
from django.conf.urls import url
from django.http import HttpResponse
from django.shortcuts import render
from .models import Student, Preference
import settings, csv, StringIO, xlsxwriter, io, re, types, json
from constance import config

# Load the Google API's
import httplib2
from apiclient import discovery
from oauth2client.file import Storage

class GoogleDrive(object):
    def __init__(self):
        self.http = Storage(settings.BASE_DIR + '/google_credentials.json').get().authorize(httplib2.Http())
        self.drive = discovery.build('drive', 'v3', http=self.http)
        self.sheets = discovery.build('sheets', 'v4', http=self.http)

    def get_spreadsheets(self):
        """
        Get an array like:
        [ {'id': <string: Google Drive ID of the spreadsheet, the one also in the url>,
           'name': <string: The name given by the user to the spreadsheet>
           'webViewLink': <string: A url where the user can edit the spreadsheet in a browser>
        }]
        """
        return self.drive.files().list(
            q="'{0}' in parents and mimeType = 'application/vnd.google-apps.spreadsheet'".format(config.GOOGLE_DRIVE_FOLDER),
            fields="files(id, name, webViewLink)",
            orderBy="name"
            ).execute()['files']

    def get_sheets(self, spreadsheet_id):
        worksheets = self.sheets.spreadsheets().get(
            spreadsheetId=spreadsheet_id).execute()['sheets']

        return [s['properties']['title'] for s in worksheets]

    def get_students(self, spreadsheet_id):
        """
        Return an array with all the students in the sheet, ordered by

        like this:
        [{'title': <string: name for the term>, 'students': [
                {'studentnumber': <int>, 'name': <string>},
                ...
             },
             ...
        """
        worksheets = self.sheets.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            includeGridData=True).execute()['sheets']

        students = []
        for sheet in worksheets:
            sheet_title = sheet['properties']['title']

            for row in sheet['data'][0]['rowData'][1:]:
                if 'values' in row:
                    studentnumber = row['values'][0].get('formattedValue') or ''

                    if studentnumber <> '':
                        try:
                            firstname = row['values'][3].get('formattedValue') or ''
                            lastname_prefix = row['values'][2].get('formattedValue') or ''
                            lastname = row['values'][1].get('formattedValue') or ''
                            email = row['values'][4].get('formattedValue') or ''

                            name = firstname
                            if lastname_prefix <> '':
                                name += ' ' + lastname_prefix

                            if lastname <> '':
                                name += ' ' + lastname


                            student = {
                                'student_number': int(studentnumber),
                                'name': name,
                                'sheet': sheet_title,
                                'email': email
                            }
                            students.append(student)
                        except:
                            pass

        return students

googledrive = GoogleDrive()

def sort_by_sheet(students):
    """
    Gets a list like:
    [
        {'student_number': <int>, 'name': <string>, 'sheet': <string>},
        {'student_number': <int>, 'name': <string>, 'sheet': <string>},
        ...
    ]
    and transforms it to:
    [
        {'sheet': <string>, 'students':
            [
                {'student_number': <int>, 'name': <string>, 'sheet': <string>},
                {'student_number': <int>, 'name': <string>, 'sheet': <string>},
                ...
            ]
        },
        ...
    ]
    """
    seen = set()
    sheets = [s['sheet'] for s in students if not (s['sheet'] in seen or seen.add(s['sheet']))]

    def without_sheet(student):
        student = dict(student)
        del student['sheet']
        return student

    students = [{'sheet': sheet, 'students':
        [without_sheet(s) for s in students if s['sheet'] == sheet]
    } for sheet in sheets]

    return students

def get_difference(all_students):
    """
    Get a list of differences between the database students and the gives students
    and a list of students to be deleted

    returns a tuple like:
    [
        {'change': 'insert', 'studentnumber': <int>, 'name': <string>, 'sheet': <string>, 'email': <string>},
        {'change': 'update', 'studentnumber': <int>, 'name': <string>, 'sheet': <string>, 'email': <string>},
        ...
    ],
    [
        {'studentnumber': <int>, 'name': <string>},
        ...
    ]
    """
    twin_students = list(Student.objects.all())

    changed_students = []
    deleted_students = []
    for student in all_students:
        student['change'] = 'insert'

        # Try to look up the student in twin_students
        for twin_student in twin_students:
            if twin_student.student_number == student['student_number']:
                if twin_student.name == student['name'] and twin_student.email == student['email']:
                    student['change'] = 'nothing'
                else:
                    student['change'] = 'update'

                break

        if student['change'] != 'nothing':
            changed_students.append(student)

    all_student_numbers = [s['student_number'] for s in all_students]
    deleted_students = [
        {'student_number': s.student_number, 'name': s.name}
        for s in twin_students
        if s.student_number not in all_student_numbers]

    return changed_students, deleted_students

def get_pairs(all_students):
    """
    Get a list of all the pairs that are present in the students provided as a list of Preference objects
    """
    all_student_numbers = [s['student_number'] for s in all_students]

    all_pairs = Preference.objects.raw("""
            SELECT id, student_id, preference_for_id
            FROM twin_preference AS tp
            WHERE EXISTS(
                SELECT 1
                FROM twin_preference AS tp2
                WHERE tp.student_id = tp2.preference_for_id
                AND tp.preference_for_id = tp2.student_id)
            AND student_id < preference_for_id
            ORDER BY student_id""")

    return filter(lambda pref: pref.student.student_number in all_student_numbers and pref.preference_for.student_number in all_student_numbers, all_pairs)

def student_import(request, spreadsheet_id):
    if spreadsheet_id is None:
        return render(request, 'student_import_choose_spreadsheet.html', {'sheets': googledrive.get_spreadsheets()})

    if request.method == "POST":
        for key in request.POST:
            if key.startswith('student-upsert-'):
                student_data = json.loads(request.POST[key])
                Student.objects.update_or_create(
                    student_number=student_data['student_number'],
                    defaults={
                        'name': student_data['name'],
                        'email': student_data['email'],
                    })

            if key.startswith('student-delete-'):
                student_number = int(key.replace('student-delete-', ''))
                Student.objects.filter(student_number=student_number).delete()

    students, deleted_students = get_difference(googledrive.get_students(spreadsheet_id))
    students = sort_by_sheet(students)
    return render(request, 'student_import_confirm_changes.html',
        {'students': students, 'deleted_students': deleted_students})


"""
Generates a 2-dimensional array that can be given to the user as output
It takes as input a list of all students in dictionary form,
and the sheet that is supposed to be outputted

It outputs an array of the following format:
[
    ['1a', 2077000, 'Paul',     'IN01', 'koppel'],
    ['1b', 2077043, 'Bob',      'IN01', 'koppel']
    ['2a', 2076032, 'Reinier',  'IN01', 'mismatch']
    ['2a', 2076246, 'Rob',      'IN01', 'mismatch']
    ['3',  2079414, 'Bart',     'IN01', 'single']
    ['4',  2079446, 'Stijn',    'IN01', 'single']
]
The columns are as follows:
- Pair number
- Student number
- Student name
- Sheet the student is originating from
- Status

The status can be one of three things: (always in the given order)
* 'koppel'
   These are two students that have chosen eachother as a preference
   and are both from the given sheet. They have matching pair numbers (a and b)
* 'mismatch'
   These are two students that have chosen eachother as a preference,
   but only one of them is from the given sheet
* 'single'
   These are all the students that are not part of a pair
"""
def array_excel_output(all_students, sheet):
    pairs = get_pairs(all_students)
    sheet_student_numbers = [s['student_number'] for s in all_students if s['sheet'] == sheet]

    paired_student_numbers = set()
    for pair in pairs:
        paired_student_numbers.add(pair.student.student_number)
        paired_student_numbers.add(pair.preference_for.student_number)

    sheet_lookup = {}
    for student in all_students:
        sheet_lookup[student['student_number']] = student['sheet']

    output = []
    pair_number = 1

    # First do all the 'koppels'
    for pair in pairs:
        if pair.student.student_number in sheet_student_numbers \
            and pair.preference_for.student_number in sheet_student_numbers:
            output.append(['{0}a'.format(pair_number), pair.student.student_number, pair.student.name, sheet, 'koppel'])
            output.append(['{0}b'.format(pair_number), pair.preference_for.student_number, pair.preference_for.name, sheet, 'koppel'])
            pair_number += 1

    # Then do all the mismatches
    for pair in pairs:
        if (pair.student.student_number in sheet_student_numbers) \
            ^ (pair.preference_for.student_number in sheet_student_numbers):
            output.append(['{0}a'.format(pair_number), pair.student.student_number, pair.student.name, sheet_lookup[pair.student.student_number], 'mismatch'])
            output.append(['{0}b'.format(pair_number), pair.preference_for.student_number, pair.preference_for.name, sheet_lookup[pair.preference_for.student_number], 'mismatch'])
            pair_number += 1

    # Then add all the singles
    for student in all_students:
        if student['sheet'] == sheet and student['student_number'] not in paired_student_numbers:
            output.append([str(pair_number), student['student_number'], student['name'], sheet, 'single'])
            pair_number += 1

    return output

def make_groups(request, spreadsheet_id):
    if spreadsheet_id is None:
        return render(request, 'make_groups_choose_spreadsheet.html', {'sheets': googledrive.get_spreadsheets()})

    students = googledrive.get_students(spreadsheet_id)

    seen = set()
    sheets = [s['sheet'] for s in students if not (s['sheet'] in seen or seen.add(s['sheet']))]

    output = io.BytesIO()
    workbook = xlsxwriter.workbook.Workbook(output, {'in_memory': True})

    for sheet in sheets:
        excel_output = array_excel_output(students, sheet)

        worksheet = workbook.add_worksheet(re.sub(r'[^\w\']', '', sheet))
        row_i = 0
        for row in excel_output:
            worksheet.write_row(row_i, 0, row)
            row_i += 1

        worksheet.set_column(0, 0, 3)
        worksheet.set_column(2, 2, 30)
        worksheet.set_column(3, 3, 14)
    workbook.close()
    output.seek(0)

    response = HttpResponse(output.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response['Content-Disposition'] = "attachment; filename=twin.xlsx"

    return response

def get_urls(self):
    urls = [
        url(r'^twin/student/import(?:/([^/]+))?', student_import),
        url(r'^twin/groups(?:/([^/]+))?', make_groups)
    ]

    return urls + admin.AdminSite.get_urls(self)

admin.site.site_header = 'TWIN administratie'
admin.site.index_template = 'admin_index.html'
admin.site.get_urls = types.MethodType(get_urls, admin.site)

admin.site.register(Student)
admin.site.register(Preference)
