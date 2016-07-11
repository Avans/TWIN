from django.contrib.admin import AdminSite, ModelAdmin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from import_export.fields import Field
from .models import Student

class TwinAdminSite(AdminSite):
    site_header = 'TWIN administratie'

class StudentResource(resources.ModelResource):
    studentnummer = Field(attribute='student_number')
    naam = Field(attribute='name')

    class Meta:
        model = Student
        import_id_fields = ('studentnummer',)
        fields = ('studentnummer','email', 'naam')
        export_order = fields


class StudentAdmin(ImportExportModelAdmin):
    resource_class = StudentResource






site = TwinAdminSite(name='admin')
site.register(Student, StudentAdmin)