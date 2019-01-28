from typing import Optional, Union
from django.contrib.postgres.fields import JSONField
from django.db import models
from server import minio
from server.models import loaded_module
from server.modules.types import ProcessResult
from .fields import ColumnsField
from .Params import Params
from .param_field import ParamDTypeDict, ParamField
from .CachedRenderResult import CachedRenderResult
from .module_version import ModuleVersion
from .StoredObject import StoredObject
from .Tab import Tab
from .Workflow import Workflow


class WfModule(models.Model):
    """An instance of a Module in a Workflow."""
    class Meta:
        ordering = ['order']

    def __str__(self):
        # Don't use DB queries here.
        return 'wf_module[%d] at position %d' % (self.id, self.order)

    @property
    def workflow(self):
        return Workflow.objects.get(tabs__wf_modules__id=self.id)

    @property
    def workflow_id(self):
        return self.tab.workflow_id

    @property
    def tab_slug(self):
        return self.tab.slug

    @classmethod
    def live_in_workflow(cls,
                         workflow: Union[int, Workflow]) -> models.QuerySet:
        """
        QuerySet of not-deleted WfModules in `workflow`.

        You may specify `workflow` by its `pk` or as an object.

        Deleted WfModules and WfModules in deleted Tabs will omitted.
        """
        if isinstance(workflow, int):
            workflow_id = workflow
        else:
            workflow_id = workflow.pk

        return cls.objects.filter(
            tab__workflow_id=workflow_id,
            tab__is_deleted=False,
            is_deleted=False
        )

    tab = models.ForeignKey(
        Tab,
        related_name='wf_modules',
        on_delete=models.CASCADE
    )

    module_id_name = models.CharField(max_length=200, default='')

    order = models.IntegerField()

    notes = models.TextField(
        null=True,
        blank=True)

    stored_data_version = models.DateTimeField(
        null=True,
        blank=True)                      # we may not have stored data

    # drives whether the module is expanded or collapsed on the front-end.
    is_collapsed = models.BooleanField(
        default=False,
        blank=False,
        null=False
    )

    is_deleted = models.BooleanField(default=False, null=False)

    # For modules that fetch data: how often do we check for updates, and do we
    # switch to latest version automatically
    auto_update_data = models.BooleanField(default=False)

    # when should next update run?
    next_update = models.DateTimeField(null=True, blank=True)
    # time in seconds between updates, default of 1 day
    update_interval = models.IntegerField(default=86400)
    last_update_check = models.DateTimeField(null=True, blank=True)

    # true means, 'email owner when output changes'
    notifications = models.BooleanField(default=False)

    # true means user has not acknowledged email
    has_unseen_notification = models.BooleanField(default=False)

    cached_render_result_delta_id = models.IntegerField(null=True, blank=True)
    cached_render_result_status = models.CharField(
        null=True,
        blank=True,
        choices=[('ok', 'ok'), ('error', 'error'),
                 ('unreachable', 'unreachable')],
        max_length=20
    )
    cached_render_result_error = models.TextField(blank=True)
    # should be JSONField but we need backwards-compatibility
    cached_render_result_json = models.BinaryField(blank=True)
    cached_render_result_quick_fixes = JSONField(blank=True, default=list)
    cached_render_result_columns = ColumnsField(null=True, blank=True)
    cached_render_result_nrows = models.IntegerField(null=True, blank=True)

    # TODO once we auto-compute stale module outputs, nix is_busy -- it will
    # be implied by the fact that the cached output revision is wrong.
    is_busy = models.BooleanField(default=False, null=False)

    # There's fetch_error and there's cached_render_result_error.
    fetch_error = models.CharField('fetch_error', max_length=2000, blank=True)

    # Most-recent delta that may possibly affect the output of this module.
    # This isn't a ForeignKey because many deltas have a foreign key pointing
    # to the WfModule, so we'd be left with a chicken-and-egg problem.
    last_relevant_delta_id = models.IntegerField(default=0, null=False)

    params = JSONField(default={})
    secrets = JSONField(default={})

    @property
    def module_version(self):
        if not hasattr(self, '_module_version'):
            try:
                self._module_version = ModuleVersion.objects.latest(
                    self.module_id_name
                )
            except ModuleVersion.DoesNotExist:
                self._module_version = None

        return self._module_version

    @property
    def output_status(self):
        """
        Return 'ok', 'busy', 'error' or 'unreachable'.

        'busy': render is pending
        'error': render produced an error and no table
        'unreachable': a previous module had 'error' so we will not run this
        'ok': render produced a table
        """
        if not self.get_cached_render_result(only_fresh=True):
            return 'busy'
        else:
            return self.cached_render_result_status

    @property
    def output_error(self):
        if not self.get_cached_render_result(only_fresh=True):
            return ''
        else:
            return self.cached_render_result_error

    # ---- Authorization ----
    # User can access wf_module if they can access workflow
    def request_authorized_read(self, request):
        return self.workflow.request_authorized_read(request)

    def request_authorized_write(self, request):
        return self.workflow.request_authorized_write(request)

    # ---- Data versions ----
    # Modules that fetch data, like Load URL or Twitter or scrapers, store
    # versions of all previously fetched data

    # Note: does not switch to new version automatically
    def store_fetched_table(self, table):
        stored_object = StoredObject.create_table(self, table)
        return stored_object.stored_at

    # Compares against latest version (which may not be current version)
    # Note: does not switch to new version automatically
    def store_fetched_table_if_different(self, table, metadata=''):
        reference_so = StoredObject.objects.filter(
            wf_module=self
        ).order_by('-stored_at').first()

        new_version = StoredObject.create_table_if_different(self,
                                                             reference_so,
                                                             table,
                                                             metadata=metadata)
        return new_version.stored_at if new_version else None

    def retrieve_fetched_table(self):
        try:
            return self.stored_objects.get(
                stored_at=self.stored_data_version
            ).get_table()
        except StoredObject.DoesNotExist:
            # Either self.stored_data_version is None or it has been deleted.
            return None

    def get_fetch_result(self) -> Optional[ProcessResult]:
        """Load the result of a Fetch, if there was one."""
        table = self.retrieve_fetched_table()
        if table is None:
            return None

        return ProcessResult(table, self.fetch_error)

    def list_fetched_data_versions(self):
        return list(self.stored_objects
                    .order_by('-stored_at')
                    .values_list('stored_at', 'read'))

    def get_params(self) -> Params:
        """
        Generate valid parameters (reading from the database) for easy access.

        Raise ValueError on _programmer_ error. That's usually the module
        author's problem, and we'll want to display the error to the user so
        the user can pester the module author.
        """
        if self.module_version is None:
            return Params(ParamDTypeDict({}), {}, {})

        schema = self.module_version.param_schema
        lm = (
            # we don't import LoadedModule directly, because we'll mock it
            # out in unit tests.
            loaded_module.LoadedModule.for_module_version_sync(
                self.module_version
            )
        )
        # raises ValueError
        values = lm.migrate_params(schema, self.params)

        # "migrate" secrets: exactly the id_names specified in module_version
        # spec, with values maybe None
        secrets = {}
        for field in self.module_version.param_fields:
            if field.ftype == ParamField.FType.SECRET:
                secrets[field.id_name] = self.secrets.get(field.id_name)

        return Params(schema, values, secrets)

    # re-render entire workflow when a module goes ready or error, on the
    # assumption that new output data is available
    def set_ready(self):
        self.is_busy = False
        self.fetch_error = ''
        self.save(update_fields=['is_busy', 'fetch_error'])

    # --- Duplicate ---
    # used when duplicating a whole workflow
    def duplicate(self, to_tab):
        to_workflow = to_tab.workflow

        # Initialize but don't save
        new_wfm = WfModule(
            tab=to_tab,
            module_id_name=self.module_id_name,
            fetch_error=self.fetch_error,
            stored_data_version=self.stored_data_version,
            order=self.order,
            notes=self.notes,
            is_collapsed=self.is_collapsed,
            auto_update_data=False,
            next_update=self.next_update,
            update_interval=self.update_interval,
            last_update_check=self.last_update_check,
            # to_workflow has exactly one delta, and that's the version of all
            # its modules. This is so we can cache render results. (Cached
            # render results require a delta ID.)
            last_relevant_delta_id=to_workflow.last_delta_id,
            params=self.params,
            secrets={}  # DO NOT COPY SECRETS
        )

        # Copy cached render result, if there is one.
        #
        # If we duplicate a Workflow mid-render, the cached render result might
        # not have any useful data. But that's okay: just kick off a new
        # render. The common case (all-rendered Workflow) will produce a
        # fully-rendered duplicate Workflow.
        #
        # get_cached_render_result() does not check for the existence of
        # Parquet files. But it does let us access `.parquet_key`.
        cached_result = self.get_cached_render_result(only_fresh=True)
        if cached_result:
            # assuming file-copy succeeds, copy cached results.
            # Not using `new_wfm.cache_render_result(cached_result.result)`
            # because that would involve reading the whole thing.
            new_wfm.cached_render_result_delta_id = \
                to_workflow.last_delta_id
            for attr in ('status', 'error', 'json', 'quick_fixes', 'columns',
                         'nrows'):
                full_attr = f'cached_render_result_{attr}'
                setattr(new_wfm, full_attr, getattr(self, full_attr))

            new_wfm.save()  # so there is a new_wfm.id for parquet_key

            parquet_key = new_wfm.get_cached_render_result().parquet_key

            try:
                minio.minio_client.copy_object(
                    minio.CachedRenderResultsBucket,
                    parquet_key,
                    '%(Bucket)s/%(Key)s' % {
                        'Bucket': minio.CachedRenderResultsBucket,
                        'Key': cached_result.parquet_key,
                    }
                )
            except minio.error.NoSuchKey:
                # DB and filesystem are out of sync. CachedRenderResult handles
                # such cases gracefully. So `new_result` will behave exactly
                # like `cached_result`.
                pass

        new_wfm.save()

        # Duplicate the current stored data only, not the history
        if self.stored_data_version is not None:
            self.stored_objects.get(stored_at=self.stored_data_version) \
                    .duplicate(new_wfm)

        return new_wfm

    def get_cached_render_result(self, only_fresh=False) -> CachedRenderResult:
        """Load this WfModule's CachedRenderResult from disk."""
        result = CachedRenderResult.from_wf_module(self)

        if not result:
            return None

        if only_fresh and result.delta_id != self.last_relevant_delta_id:
            return None

        return result

    def cache_render_result(self, delta_id: Optional[int],
                            result: ProcessResult) -> CachedRenderResult:
        """Save the given ProcessResult (or None) for later viewing."""
        return CachedRenderResult.assign_wf_module(self, delta_id, result)

    def delete(self, *args, **kwargs):
        self.cache_render_result(None, None)
        super().delete(*args, **kwargs)
