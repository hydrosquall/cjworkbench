from django.contrib import admin
from .models import ModuleVersion, WfModule, StoredObject, Delta, Workflow

admin.site.register(ModuleVersion)
admin.site.register(WfModule)
admin.site.register(StoredObject)
admin.site.register(Delta)


class WorkflowAdmin(admin.ModelAdmin):
    # don't load load every delta ever on the workflow object page
    raw_id_fields = ("last_delta",)

    search_fields = ('name', 'owner__username', 'owner__email')
    list_filter = ('owner',)


admin.site.register(Workflow, WorkflowAdmin)
