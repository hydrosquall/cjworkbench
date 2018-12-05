# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-11-27 20:33
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):
    """
    Make wf_module.workflow_id NOT NULL.

    Previously, we'd set workflow_id = NULL when "deleting" (an undo-able
    operation). This was convenient, but it was frustrating: e.g., we stored
    workflow_id elsewhere (cached_render_result_workflow_id) so we could read
    and write files. In truth, `workflow_id` is an essential aspect of
    WfModule, even when the WfModule is deleted.

    To migrate, we need to _recover_ previously-deleted WfModules -- which are
    all orphans except for references within Deltas. For each deleted WfModule,
    we attempt to match:

        1. cached_render_result_workflow_id
        2. delta.wf_module_id, joined by last_relevant_delta_id
        3. delta.wf_module_id, joined by (UNION of all Commands that have a
           wf_module_id)

    (These numbers are always either NULL or equivalent, so we can COALESCE
    them in any order we like.)
    """

    dependencies = [
        ('server', '0140_auto_20181127_2031'),
    ]

    operations = [
        migrations.RunSQL([
            """
            WITH commands AS (
                SELECT wf_module_id, delta_ptr_id FROM server_addmodulecommand
                UNION
                SELECT wf_module_id, delta_ptr_id FROM server_changedataversioncommand
                UNION
                SELECT wf_module_id, delta_ptr_id FROM server_changeparameterscommand
                UNION
                SELECT wf_module_id, delta_ptr_id FROM server_changewfmodulenotescommand
                UNION
                SELECT wf_module_id, delta_ptr_id FROM server_changewfmoduleupdatesettingscommand
                UNION
                SELECT wf_module_id, delta_ptr_id FROM server_deletemodulecommand
                UNION
                SELECT p.wf_module_id, d.delta_ptr_id FROM server_changeparametercommand d
                INNER JOIN server_parameterval p ON d.parameter_val_id = p.id
            ),
            commands2 AS (
                SELECT commands.wf_module_id, d.workflow_id
                FROM commands
                INNER JOIN server_delta d ON commands.delta_ptr_id = d.id
            ),
            wf_module_workflows AS (
                SELECT DISTINCT
                    wfm.id AS wf_module_id,
                    COALESCE(
                        wfm.workflow_id,
                        wfm.cached_render_result_workflow_id,
                        server_delta.workflow_id,
                        commands2.workflow_id
                    ) AS workflow_id
                FROM server_wfmodule wfm
                LEFT JOIN server_delta
                       ON wfm.last_relevant_delta_id = server_delta.id
                LEFT JOIN commands2
                       ON wfm.id = commands2.wf_module_id
            )
            UPDATE server_wfmodule wfm
            SET
                is_deleted = TRUE,
                workflow_id = (
                    SELECT ww.workflow_id
                    FROM wf_module_workflows ww
                    WHERE ww.wf_module_id = wfm.id
                    AND ww.workflow_id IN (SELECT id FROM server_workflow)
                )
            WHERE wfm.workflow_id IS NULL
            """,
            # Now the only orphaned WfModules are _truly_ lost. We can't debug
            # what happened because there's no reference to them anywhere and
            # we don't even know their workflow ID so we can't look through the
            # workflow history for clues.
            #
            # Delete those WfModules. Don't worry -- they're certain not to
            # be referenced by any foreign keys.
            """
            DELETE FROM server_parameterval
            WHERE wf_module_id IN (
                SELECT id FROM server_wfmodule WHERE workflow_id IS NULL
            )
            """,
            # Leave written StoredObjects stranded. [adamhooper, 2018-11-27] I
            # assume there are plenty of orphan files anyway, so what's another
            # 7? (There are only 7 on production.)
            """
            DELETE FROM server_storedobject
            WHERE wf_module_id IN (
                SELECT id FROM server_wfmodule WHERE workflow_id IS NULL
            )
            """,
            # [adamhooper, 2018-11-27] there aren't any orphan UploadedFiles on
            # production. But we'll put the query anyway.
            """
            DELETE FROM server_uploadedfile
            WHERE wf_module_id IN (
                SELECT id FROM server_wfmodule WHERE workflow_id IS NULL
            )
            """,
            """
            DELETE FROM server_wfmodule WHERE workflow_id IS NULL
            """
        ], reverse_sql=[
            """
            UPDATE server_wfmodule
            SET
                cached_render_result_workflow_id = CASE
                    WHEN cached_render_result_delta_id IS NULL THEN NULL
                    ELSE workflow_id
                END,
                workflow_id = NULL
            WHERE is_deleted
            """
        ], elidable=True),
    ]
