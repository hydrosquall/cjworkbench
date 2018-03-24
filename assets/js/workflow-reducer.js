// Reducer for Workflow page.
// That is, provides all the state transition functions that are executed on user command
import { getPageID, nonce } from './utils'
import WorkbenchAPI from './WorkbenchAPI'
import { createStore, applyMiddleware } from 'redux'
import promiseMiddleware from 'redux-promise-middleware'
import thunk from 'redux-thunk'
import { newContext } from 'immutability-helper'

// Workflow
const INITIAL_LOAD_WORKFLOW = 'INITIAL_LOAD_WORKFLOW';
const RELOAD_WORKFLOW = 'RELOAD_WORKFLOW';
const ADD_MODULE = 'ADD_MODULE';
const DELETE_MODULE = 'DELETE_MODULE';
const SET_SELECTED_MODULE = 'SET_SELECTED_MODULE';
const SET_WORKFLOW_PUBLIC = 'SET_WORKFLOW_PUBLIC';
const SET_WF_LIBRARY_COLLAPSE = 'SET_WF_LIBRARY_COLLAPSE';
const REORDER_WFMODULES = 'REORDER_WFMODULES';

// User
const GET_CURRENT_USER = 'GET_CURRENT_USER';
const DISCONNECT_CURRENT_USER = 'DISCONNECT_CURRENT_USER';

// Module
const SET_WF_MODULE_STATUS = 'SET_WF_MODULE_STATUS';
const SET_WF_MODULE_COLLAPSED = 'SET_WF_MODULE_COLLAPSED';
const UPDATE_WF_MODULE = 'UPDATE_WF_MODULE';

// Parameter
const SET_PARAM_VALUE = 'SET_PARAM_VALUE';

// Data versions/notifications
const GET_DATA_VERSIONS = 'GET_DATA_VERSIONS';
const SET_DATA_VERSION = 'SET_DATA_VERSION';
const MARK_DATA_VERSIONS_READ = 'MARK_DATA_VERSIONS_READ';
const CLEAR_NOTIFICATIONS = 'CLEAR_NOTIFICATIONS';

let api = WorkbenchAPI(); // var so it can be mocked for testing

export function mockAPI(mock_api) {
  api = mock_api;
}

// ---- Our Store ----
// Master state for the workflow. Export so that components can store.dispatch()
// var so it can be mocked for testing
export var store = createStore(workflowReducer, window.initState, applyMiddleware( promiseMiddleware(), thunk ));

export function mockStore(mock_store) {
  store = mock_store;
}

const reducerFunc = {};

const registerReducerFunc = (key, func) => {
  reducerFunc[key] = func;
};

const nonces = [];
const generateNonce = (prefix) => {
  // Generate a nonce with some prefix from
  // the object we're creating the nonce for
  let returnNonce = nonce(prefix);
  // If it's not in the list,
  if (nonces.indexOf(returnNonce) === -1) {
    // Add it (since we know it's unique)
    nonces.push(returnNonce);
    // And return it
    return returnNonce;
  // Otherwise,
  } else {
    // try again
    return generateNonce(prefix);
  }
};
const removeNonce = (nonce) => {
  let nonceIndex = nonces.indexOf(nonce);
  if (nonceIndex !== -1) {
    nonces.splice(nonceIndex, 1);
  }
};

const update = newContext();
update.extend('$swap', function(value, original) {
  let oldIndex, newIndex;
  [oldIndex, newIndex] = value;
  let newArray = original.slice();
  newArray.splice(newIndex, 0, newArray.splice(oldIndex, 1)[0]);
  return newArray;
});

// ---- Utilities ----

export function findIdxByProp(searchArray, searchProp, searchValue) {
  let returnIdx;
  for (let i = 0; i < searchArray.length; i++) {
    if (searchArray[i][searchProp] === searchValue) {
      returnIdx = i;
      break;
    }
  }
  return returnIdx;
};


// ---- Actions ----

// -- Workflow --


// INITIAL_LOAD_WORKFLOW
// Load the workflow for the first time
export function initialLoadWorkflowAction() {
  return {
    type: INITIAL_LOAD_WORKFLOW,
    payload: api.loadWorkflow(getPageID())
  }
}
registerReducerFunc(INITIAL_LOAD_WORKFLOW + '_FULFILLED', (state, action) => {
  // Sets the selected module from backend if it exists, or the first module if there are any at all
  console.log("INITIAL_LOAD_WORKFLOW");
  let selectedWfModule = null;

  if (action.payload.selected_wf_module) {
    selectedWfModule = action.payload.selected_wf_module;
  } else if (action.payload.wf_modules && action.payload.wf_modules.length) {
    selectedWfModule = action.payload.wf_modules[0].id;
  }

  return Object.assign({}, state, {
    selected_wf_module: selectedWfModule,
    workflow: action.payload
  });
});

// RELOAD_WORKFLOW
// Re-load the workflow
// TODO: Do we need both initial and reload?
export function reloadWorkflowAction() {
  return {
    type: RELOAD_WORKFLOW,
    payload: api.loadWorkflow(getPageID()).then((json) => {return json})
  }
}
registerReducerFunc(RELOAD_WORKFLOW + '_FULFILLED', (state, action) => {
  console.log("RELOAD_WORKFLOW");
  console.log("new workflow revision " + action.payload.revision);
  /*var selectedWfModule = null;
  if (action.payload.selected_wf_module) {
    selectedWfModule = action.payload.selected_wf_module;
  } else if (action.payload.wf_modules && action.payload.wf_modules.length) {
    selectedWfModule = action.payload.wf_modules[0].id;
  };*/
  return update(state, {
    //selected_wf_module: {$set: selectedWfModule},
    workflow: {$merge: action.payload}
  });
});

// SET_WORKFLOW_PUBLIC
// Set the workflow to public or private
export function setWorkflowPublicAction(workflowId, isPublic) {
  return function (dispatch) {
    return (

      dispatch({
        type: SET_WORKFLOW_PUBLIC,
        payload: api.setWorkflowPublic(workflowId, isPublic)
      }).then( () => {

      dispatch(
        reloadWorkflowAction()
      )

    }));

  }
}

// REORDER_WFMODULES
// Re-order the modules in the module stack
export function reorderWfModulesAction(wfModuleID, newIndex) {
  let state = store.getState();
  let wfModuleIdx = findIdxByProp(state.workflow.wf_modules, 'id', wfModuleID);
  if (wfModuleIdx === newIndex) {
    return {
      type: 'NOOP'
    };
  }
  if (wfModuleIdx < newIndex) {
    newIndex -= 1;
  }
  let newState = update(state, {
    workflow: {
      wf_modules: {$swap: [wfModuleIdx, newIndex]}
    }
  });
  let newOrder = newState.workflow.wf_modules.map( (item, i) => {return { id: item.id, order: i } } );

  return {
    type: REORDER_WFMODULES,
    payload: {
      promise: api.reorderWfModules(getPageID(), newOrder),
      data: newState.workflow.wf_modules
    }
  }
}
registerReducerFunc(REORDER_WFMODULES + '_PENDING', (state, action) => {
  return update(state, {
    workflow: {
      wf_modules: {$set: action.payload}
    }
  });
});

// ADD_MODULE
// Add a module, then save the new module as the selected workflow
export function addModuleAction(moduleId, insertBefore, placeholder) {
  return function (dispatch) {
    // Generate a nonce so we can replace the correct placeholder on
    // the other end
    let nonce = generateNonce(moduleId);

    let payload = {
      promise: api.addModule(getPageID(), moduleId, insertBefore)
        .then((response) => {
          response.pendingId = nonce;
          return response;
        }),
    };

    if (typeof placeholder !== 'undefined') {
      payload.data = placeholder;
    } else {
      payload.data = {}
    }

    payload.data.placeholder = true;
    payload.data.insert_before = insertBefore;
    payload.data.pendingId = nonce;

    return (

      dispatch({
        type: ADD_MODULE,
        payload: payload
      }).then( ({value}) => {

      dispatch(
        setSelectedWfModuleAction(value.id)
      );

    }));
  }
}
registerReducerFunc(ADD_MODULE + '_PENDING', (state, action) => {
  let insertBefore = action.payload.insert_before;

  if (insertBefore === null) {
    insertBefore = state.workflow.wf_modules.length - 1;
  }

  delete action.payload.insert_before;

  return update(state, {
    workflow: {
      wf_modules: { $splice:[ [insertBefore, 0, action.payload] ] }
    }
  });
});
registerReducerFunc(ADD_MODULE + '_FULFILLED', (state, action) => {
  let insertBefore,
      overwrite = 1;

  insertBefore = findIdxByProp(state.workflow.wf_modules, 'pendingId', action.payload.pendingId);

  if (typeof insertBefore === 'undefined') {
    // There's no placeholder. Maybe one of our collaborators added this module
    // on a different client
    overwrite = 0;
    insertBefore = action.payload.insert_before;
  } else {
    removeNonce(action.payload.pendingId);
  }

  delete action.payload.insert_before;

  return update(state, {
    selected_wf_module: {$set: action.payload.id},
    workflow: {
      wf_modules: { $splice:[ [insertBefore, overwrite, action.payload] ] }
    }
  });
});


// DELETE_MODULE_ACTION
// Call delete API, then dispatch a reload
export function deleteModuleAction(id_to_delete) {
  // If we are deleting the selected module, then set previous module in stack as selected
  let newSelectedId = null;
  let state = store.getState();
  if (id_to_delete === state.selected_wf_module) {

    // Find id of previous in stack
    let wf_modules = state.workflow.wf_modules;
    for (let wfm of wf_modules) {
      if (wfm.id === id_to_delete)
        break;
      newSelectedId = wfm.id;
    }

    // if we are deleting first module, set to new first module if any
    if (newSelectedId === null) {
      if (wf_modules.length > 1) {
        newSelectedId = wf_modules[1].id;
      } else {
        newSelectedId = null; // deleting last module
      }
    }
  } else {
    // If we are not deleting the selected module, don't change selection
    newSelectedId = state.selected_wf_module;
  }

  return function (dispatch) {
    return (
      // Set the new selected module before deleting to avoid errors.
      // We do this even if the selected module isn't changing to avoid
      // writing a subtly tricky conditional here.
      dispatch(setSelectedWfModuleAction(newSelectedId)).then(() => {
      // Remove the module
      dispatch({
        type: DELETE_MODULE,
        payload: {
          promise: api.deleteModule(id_to_delete),
          data: {
            wf_module_id: id_to_delete
          }
        }
      });
    }));
  }
}
registerReducerFunc(DELETE_MODULE + '_PENDING', (state, action) => {
  let wfModuleIdx = findIdxByProp(
    state.workflow.wf_modules,
    'id',
    action.payload.wf_module_id
  );

  if (typeof wfModuleIdx === 'undefined') {
    return state;
  }

  return update(state, {
    workflow: {
      wf_modules: {$splice: [[wfModuleIdx, 1]] }
    }
  });
});


// SET_SELECTED_MODULE
// Set the selected module in the workflow
export function setSelectedWfModuleAction(wfModuleID) {
  let workflowID = store.getState().workflow.id;
  return {
    type : SET_SELECTED_MODULE,
    payload : {
      promise: api.setSelectedWfModule(workflowID, wfModuleID),
      data: {
        wf_module_id: wfModuleID
      }
    }
  }
}
registerReducerFunc(SET_SELECTED_MODULE + '_PENDING', (state, action) => {
  if (!('selected_wf_module' in state) || (action.payload.wf_module_id !== state.selected_wf_module)) {
    return update(state, {
      selected_wf_module: {$set: action.payload.wf_module_id}
    });
  } else {
    return state;
  }
});


// SET_WF_LIBRARY_COLLAPSE
// Toggle collapse of Module Library
export function setWfLibraryCollapseAction(workflow_id, isCollapsed, isReadOnly) {
  let payload = {
    data : { id: workflow_id, module_library_collapsed: isCollapsed }
  };

  if (!isReadOnly) {
    payload.promise = api.setWfLibraryCollapse(workflow_id, isCollapsed);
  }
  return {
    type : SET_WF_LIBRARY_COLLAPSE,
    payload
  }
}
registerReducerFunc(SET_WF_LIBRARY_COLLAPSE + '_PENDING', (state, action) => {
  return update(state, {
    workflow: 
      {module_library_collapsed: {$set: action.payload.module_library_collapsed}
  }});
});



// -- User --


// GET_CURRENT_USER
// Grab the JSON serialization of the current user data from the server
export function getCurrentUserAction() {
  return {
    type: GET_CURRENT_USER,
    payload: api.currentUser()
  }
}
registerReducerFunc(GET_CURRENT_USER + '_FULFILLED', (state, action) => {
  if (state.loggedInUser !== action.payload) {
    return update(state, {
      loggedInUser: {$set: action.payload}
    });
  } else {
    return state;
  }
});


// DISCONNECT_CURRENT_USER
// Delete a credential object to a third-party service on the user.
// Currently only used for Google credentials.
export function disconnectCurrentUserAction(credentialId) {
  return {
    type: DISCONNECT_CURRENT_USER,
    payload: {
      promise: api.disconnectCurrentUser( credentialId ),
      data: {
        credential_id: credentialId
      }
    }
  }
}
registerReducerFunc(DISCONNECT_CURRENT_USER + '_PENDING', (state, action) => {
  let credentialIndex

  if (action.payload.credential_id) {
    credentialIndex = state.loggedInUser.google_credentials.indexOf(action.payload.credential_id);
  }

  if (credentialIndex >= 0) {
    return update(state, {
      loggedInUser: {
        google_credentials: { $splice: [[credentialIndex, 1]] }
      }
    });
  }

  return state;
});

// -- Workflow Module --

// UPDATE_WF_MODULE
// Patch a workflow module with new data

// TODO: We don't validate which fields or types are on
// a WfModule here. The backend will reject nonexistent
// fields, but should we do something on the frontend?
export function updateWfModuleAction(id, data) {
  return {
    type: UPDATE_WF_MODULE,
    payload: {
      promise: api.updateWfModule( id, data ),
      data: {
        id,
        data
      }
    }
  };
}
registerReducerFunc(UPDATE_WF_MODULE + '_PENDING', (state, action) => {
  let moduleIdx = findIdxByProp(
    state.workflow.wf_modules,
    'id',
    action.payload.id
  );

  if (typeof moduleIdx !== 'undefined') {
    return update(state, {
      workflow: {
        wf_modules: {
          [moduleIdx]: { $merge: action.payload.data }
        }
      }
    });
  }

  return state;
});


// SET_WF_MODULE_STATUS
// Change the workflow status (OK, pending, error)
export function setWfModuleStatusAction(wfModuleID, status, error_msg='') {
  return {
    type : SET_WF_MODULE_STATUS,
    payload: {
      id : wfModuleID,
      status : status,
      error_msg: error_msg
    }
  }
}
registerReducerFunc(SET_WF_MODULE_STATUS, (state, action) => {
  if ('wf_modules' in state.workflow) {

    let wfModuleIdx = findIdxByProp(
      state.workflow.wf_modules,
      'id',
      action.payload.id
    );

    let wfModuleRef = state.workflow.wf_modules[wfModuleIdx];

    if ((wfModuleRef.status !== action.payload.status) ||
      (wfModuleRef.status === 'error' && wfModuleRef.error_msg !== action.payload.error_msg)) {

      // Create a copy of the wf_module with new status
      let newWfmProps = {status: action.payload.status, error_msg: action.payload.error_msg};

      return update(state, {
        workflow: {
          wf_modules: {
            [wfModuleIdx]: {$merge: newWfmProps}
          }
        }
      });
    }
  } else {
    return state;
  }
});

export function setWfModuleCollapsedAction(wfModuleID, isCollapsed, isReadOnly) {
  let payload = {
    data : { wf_module_id: wfModuleID, is_collapsed: isCollapsed }
  };

  if (!isReadOnly) {
    payload.promise = api.setWfModuleCollapsed(wfModuleID, isCollapsed);
  }
  return {
    type : SET_WF_MODULE_COLLAPSED,
    payload
  }
}
registerReducerFunc(SET_WF_MODULE_COLLAPSED + '_PENDING', (state, action) => {
  if ('wf_modules' in state.workflow) {
    let wfModuleIdx = findIdxByProp(
      state.workflow.wf_modules,
      'id',
      action.payload.wf_module_id
    );

    if (typeof wfModuleIdx !== 'undefined') {
      return update(state, {
        workflow: {
          wf_modules: {
            [wfModuleIdx]: { is_collapsed: { $set: action.payload.is_collapsed } }
          }
        }
      });
    }
  }

  return state;
});

// -- Parameters --

// SET_PARAM_VALUE
export function setParamValueAction(wfModuleId, paramIdName, paramValue) {
    let state = store.getState();
    let wfModuleIdx = findIdxByProp(state.workflow.wf_modules, 'id', wfModuleId);
    let paramIdx;
    for(let i = 0; i < state.workflow.wf_modules[wfModuleIdx].parameter_vals.length; i++) {
      if (state.workflow.wf_modules[wfModuleIdx].parameter_vals[i].parameter_spec.id_name === paramIdName) {
        paramIdx = i;
        break;
      }
    }
    let paramRef = state.workflow.wf_modules[wfModuleIdx].parameter_vals[paramIdx];
    return {
      type: SET_PARAM_VALUE,
      payload: {
        promise: api.onParamChanged(paramRef.id, {value: paramValue}),
        data: {
          wfModuleId,
          paramId: paramRef.id,
          paramValue
        }
      }
    }
}
registerReducerFunc(SET_PARAM_VALUE + '_PENDING', (state, action) => {
  let wfModuleIdx, paramIdx;

  // TODO: We're finding these values twice because we don't want to depend on the
  // indexes of the wfmodule or paramaterval we got in the action creator.
  // One way to fix this would be to pass the parameter ID to the action creator
  // directly instead of module ID and parameter ID name.

  wfModuleIdx = findIdxByProp(
    state.workflow.wf_modules,
    'id',
    action.payload.wfModuleId
  );

  if (typeof wfModuleIdx !== 'undefined') {
    paramIdx = findIdxByProp(
      state.workflow.wf_modules[wfModuleIdx].parameter_vals,
      'id',
      action.payload.paramId
    );
  }

  if (typeof paramIdx !== 'undefined' &&
    action.payload.paramValue !== state.workflow.wf_modules[wfModuleIdx].parameter_vals[paramIdx].value) {
    // TODO: This is better than before, but I wonder if there's a way to store something like "indexes"
    // or "facets" on the store so we could lookup or change different kinds of objects by ID quickly
    return update(state, {
      workflow: {
        wf_modules: {
          [wfModuleIdx]: {
            parameter_vals: {
              [paramIdx]: {
                value: { $set: action.payload.paramValue }
              }
            }
          }
        }
      }
    });
  }

  return state;
});

// SET_DATA_VERSION
export function setDataVersionAction(wfModuleId, selectedVersion) {
  return {
    type: SET_DATA_VERSION,
    payload: {
      promise: api.setWfModuleVersion(wfModuleId, selectedVersion),
      data: {
        wfModuleId,
        selectedVersion
      }
    }
  }
}
registerReducerFunc(SET_DATA_VERSION + '_PENDING', (state, action) => {
  let wfModuleIdx = findIdxByProp(
    state.workflow.wf_modules,
    'id',
    action.payload.wfModuleId
  );
  return update(state, {
    workflow: {
      wf_modules: {
        [wfModuleIdx]: {
          versions: {
            selected: {$set: action.payload.selectedVersion}
          }
        }
      }
    }
  })
});

export function markDataVersionsReadAction(id, versions) {
  let versions_to_update = [].concat(versions); // will accept one or many
  return {
    type: MARK_DATA_VERSIONS_READ,
    payload: {
      promise: api.markDataVersionsRead(id, versions_to_update),
      data: {
        id,
        versions_to_update
      }
    }
  };
}
registerReducerFunc(MARK_DATA_VERSIONS_READ + '_PENDING', (state, action) => {
  let wfModuleIdx = findIdxByProp(state.workflow.wf_modules, 'id', action.payload.id);
  if (typeof wfModuleIdx !== 'undefined' &&
    typeof state.workflow.wf_modules[wfModuleIdx].versions !== 'undefined') {
    return update(state, {
      workflow: {
        wf_modules: {
          [wfModuleIdx]: {
            // Take the versions array,
            versions: { versions: { $apply: (versionsArray) => {
              // For each version,
              return versionsArray.map((version) => {
                // If this is a version we want to mark read,
                if (action.payload.versions_to_update.indexOf(version[0]) >= 0) {
                  // Set the 'read' bit to true
                  version[1] = true;
                }
                // Return the version
                return version;
              });
            }}}
          }
        }
      }
    });
  }
  return state;
});

export function clearNotificationsAction(wfModuleId) {
  return {
    type: CLEAR_NOTIFICATIONS,
    payload: {
      promise: api.deleteWfModuleNotifications(wfModuleId),
      data: {
        wfModuleId
      }
    }
  }
}
registerReducerFunc(CLEAR_NOTIFICATIONS + '_PENDING', (state, action) => {
  let wfModuleIdx = findIdxByProp(
    state.workflow.wf_modules,
    'id',
    action.payload.wfModuleId
  );
  if (typeof wfModuleIdx !== 'undefined') {
    return update(state, {
      workflow: {
        wf_modules: {
          [wfModuleIdx]: {
            notification_count: {$set: 0}
          }
        }
      }
    });
  }
  return state;
});

// ---- Reducer ----
// Main dispatch for actions. Each action mutates the state to a new state, in typical Redux fashion

export function workflowReducer(state, action) {
  if (!state) {
    state = {}; // initial state. we'll load a workflow soon.
  }

  if (reducerFunc && action.type in reducerFunc) {
    return reducerFunc[action.type](state, action);
  }

  return state;
}
