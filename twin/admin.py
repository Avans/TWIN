from django.contrib.admin import AdminSite, ModelAdmin
from django.conf.urls import url
from django.http import HttpResponse
from django.shortcuts import render
from .models import Student, Preference
import settings, csv, StringIO

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
            q="'{0}' in parents and mimeType = 'application/vnd.google-apps.spreadsheet'".format(settings.DRIVE_FOLDER),
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

                            name = firstname
                            if lastname_prefix <> '':
                                name += ' ' + lastname_prefix

                            if lastname <> '':
                                name += ' ' + lastname


                            student = {
                                'student_number': int(studentnumber),
                                'name': name,
                                'sheet': sheet_title
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
        {'change': 'insert', 'studentnumber': <int>, 'name': <string>, 'sheet': <string>},
        {'change': 'update', 'studentnumber': <int>, 'name': <string>, 'sheet': <string>},
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
                if twin_student.name == student['name']:
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
                print repr(request.POST[key])
                student_number = int(key.replace('student-upsert-', ''))
                Student.objects.update_or_create(
                    student_number=student_number,
                    defaults={'name': request.POST[key]}
                    )

            if key.startswith('student-delete-'):
                student_number = int(key.replace('student-delete-', ''))
                Student.objects.filter(student_number=student_number).delete()

    students, deleted_students = get_difference(googledrive.get_students(spreadsheet_id))
    students = sort_by_sheet(students)
    return render(request, 'student_import_confirm_changes.html',
        {'students': students, 'deleted_students': deleted_students})

def make_groups(request, spreadsheet_id, sheet):
    if spreadsheet_id is None:
        return render(request, 'make_groups_choose_spreadsheet.html', {'sheets': googledrive.get_spreadsheets()})
    elif sheet is None:
        return render(request, 'make_groups_choose_sheet.html', {'spreadsheet_id': spreadsheet_id, 'sheets': googledrive.get_sheets(spreadsheet_id)})

    students = googledrive.get_students(spreadsheet_id)
    students = [s['students'] for s in sort_by_sheet(students) if s['sheet'] == sheet][0]

    pairs = get_pairs(students)

    if 'excel' in request.GET:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{0}_twins.csv"'.format(sheet)

        csv_writer = csv.writer(response, delimiter=';', quotechar='"')
        i = 1
        for pair in pairs:
            csv_writer.writerow([i, pair.student.student_number, pair.student.name])
            csv_writer.writerow([i, pair.preference_for.student_number, pair.preference_for.name])
            i += 1

        return response

    else:

        return render(request, 'make_groups.html', {'pairs': pairs, 'sheet': sheet})


class TwinAdminSite(AdminSite):
    site_header = 'TWIN administratie'
    index_template = 'admin_index.html'

    def get_urls(self):
        urls = [
            url(r'^twin/student/import(?:/([^/]+))?', student_import),
            url(r'^twin/groups(?:/([^/]+))?(?:/(.+))?', make_groups)
        ]

        return AdminSite.get_urls(self) + urls

class Admin(ModelAdmin):
    pass

site = TwinAdminSite(name='admin')
site.register(Student)
site.register(Preference)
