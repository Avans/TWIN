from django.contrib.admin import AdminSite, ModelAdmin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from import_export.fields import Field
from import_export.widgets import Widget
from .models import Student, Term

class TwinAdminSite(AdminSite):
    site_header = 'TWIN administratie'

class TermWidget(Widget):
    def clean(self, value):
        terms = Term.objects.all()
        try:
            return [term for term in terms if str(term) == value][0]
        except:
            raise ValueError("\n\nBlok '{0}' bestaat niet. Kies uit: {1}".format(value, ', '.join(["'{0}'".format(term) for term in terms])))

    def render(self, value):
        return str(value)

class StudentResource(resources.ModelResource):
    studentnummer = Field(attribute='student_number')
    naam = Field(attribute='name')
    blok = Field(attribute='term', widget=TermWidget())

    class Meta:
        model = Student
        import_id_fields = ('studentnummer',)
        fields = ('studentnummer','email', 'naam', 'blok')
        export_order = fields


class StudentAdmin(ImportExportModelAdmin):
    resource_class = StudentResource



site = TwinAdminSite(name='admin')
site.register(Student, StudentAdmin)
site.register(Term)