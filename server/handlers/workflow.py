from typing import List
from .decorators import register_websockets_handler, websockets_handler
from .types import HandlerError
from channels.db import database_sync_to_async
from server.models import Tab, Workflow, WfModule
from server.models.commands import ChangeWorkflowTitleCommand, \
    ReorderTabsCommand
from server.versions import WorkflowRedo, WorkflowUndo


@register_websockets_handler
@websockets_handler('write')
async def undo(workflow: Workflow, **kwargs):
    await WorkflowUndo(workflow)


@register_websockets_handler
@websockets_handler('write')
async def redo(workflow: Workflow, **kwargs):
    await WorkflowRedo(workflow)


@register_websockets_handler
@websockets_handler('write')
async def set_name(workflow: Workflow, name: str, **kwargs):
    name = str(name)  # JSON input cannot cause error here
    await ChangeWorkflowTitleCommand.create(workflow=workflow, new_value=name)


@database_sync_to_async
def _write_position(workflow: Workflow, wf_module_id: int) -> None:
    """Write position in DB, or raise (Workflow|Tab|WfModule).DoesNotExist."""
    with workflow.cooperative_lock():
        wf_module = WfModule.live_in_workflow(workflow).get(pk=wf_module_id)
        tab = wf_module.tab

        tab.selected_wf_module_position = wf_module.order
        tab.save(update_fields=['selected_wf_module_position'])

        workflow.selected_tab_position = tab.position
        workflow.save(update_fields=['selected_tab_position'])


@register_websockets_handler
@websockets_handler('write')
async def set_position(workflow: Workflow, wfModuleId: int, **kwargs):
    try:
        wf_module_id = int(wfModuleId)
    except (TypeError, ValueError):
        raise HandlerError('wfModuleId must be a Number')

    try:
        await _write_position(workflow, wf_module_id)
    except (Workflow.DoesNotExist, Tab.DoesNotExist, WfModule.DoesNotExist):
        raise HandlerError('Invalid wfModuleId')


@register_websockets_handler
@websockets_handler('write')
async def set_tab_order(workflow: Workflow, tabIds: List[int], **kwargs):
    if not isinstance(tabIds, list):
        raise HandlerError('tabIds must be an Array of integers')
    for tab_id in tabIds:
        if not isinstance(tab_id, int):
            raise HandlerError('tabIds must be an Array of integers')

    try:
        await ReorderTabsCommand.create(workflow=workflow, new_order=tabIds)
    except ValueError as err:
        if str(err) == 'wrong tab IDs':
            raise HandlerError('wrong tab IDs')
        else:
            raise
