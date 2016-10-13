from django.contrib.admin import AdminSite, ModelAdmin
from django.conf.urls import url
from django.http import HttpResponse
from django.shortcuts import render
from .models import Student, Term, Preference
import settings

# Load the Google API's
import httplib2
from apiclient import discovery
from oauth2client.file import Storage

http = Storage(settings.BASE_DIR + '/google_credentials.json').get().authorize(httplib2.Http())
drive = discovery.build('drive', 'v3', http=http)
sheets = discovery.build('sheets', 'v4', http=http)

def student_import(request):
    sheet_files = drive.files().list(
        q="'{0}' in parents and mimeType = 'application/vnd.google-apps.spreadsheet'".format(settings.DRIVE_FOLDER),
        fields="files(id, name, webViewLink)",
        orderBy="name"
        ).execute()['files']

    return render(request, 'student_import_choose_sheet.html', {'sheets': sheet_files})

class TwinAdminSite(AdminSite):
    site_header = 'TWIN administratie'
    index_template = 'admin_index.html'

    def get_urls(self):
        urls = [
            url(r'^twin/student/import$', student_import),
            url(r'^twin/groups$', student_import)
        ]

        return AdminSite.get_urls(self) + urls

class Admin(ModelAdmin):
    pass

site = TwinAdminSite(name='admin')
site.register(Student)
site.register(Preference)
site.register(Term)