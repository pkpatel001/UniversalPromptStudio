"""A-005 workflow authoring, planning, execution, and persistence tests."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import cast

from Backend.core.container import create_in_memory_container, create_sqlite_container
from Backend.domain.models import PromptBlock, PromptBlockType
from Backend.infrastructure.repositories.sqlite import CURRENT_SCHEMA_VERSION, DATABASE_FILE_NAME
from Backend.infrastructure.workflow_definitions import WORKFLOW_DEFINITIONS_FILE_NAME
from Backend.ipc import (
    IPC_PROTOCOL_VERSION,
    WORKFLOW_CREATE_COMMAND,
    WORKFLOW_DELETE_COMMAND,
    WORKFLOW_EXECUTE_COMMAND,
    WORKFLOW_GET_COMMAND,
    WORKFLOW_LIST_COMMAND,
    WORKFLOW_OPERATIONS_COMMAND,
    WORKFLOW_PLAN_COMMAND,
    WORKFLOW_UPDATE_COMMAND,
    ApplicationIpcRouter,
)
from Backend.ipc.models import IpcRequest


def _call(
    router: ApplicationIpcRouter,
    command: str,
    payload: dict[str, object],
) -> dict[str, object]:
    response = router.handle(
        IpcRequest(IPC_PROTOCOL_VERSION, f"request-{command}", command, payload)  # type: ignore[arg-type]
    )
    return cast(dict[str, object], response.to_dict())


def _echo_workflow(*, edges: bool = True) -> dict[str, object]:
    workflow_edges: list[object] = []
    if edges:
        workflow_edges = [
            {
                "source": {"workflow_input": "input"},
                "target": {"node": "echo", "port": "value"},
            },
            {
                "source": {"node": "echo", "port": "value"},
                "target": {"workflow_output": "output"},
            },
        ]
    node_input = {"id": "value", "type": "string", "description": "Text supplied to the operation."}
    node_output = {
        "id": "value",
        "type": "string",
        "description": "Text returned by the operation.",
    }
    return {
        "schema_version": 1,
        "workflow": {
            "id": "ups.user-echo",
            "name": "User Echo",
            "version": "1.0.0",
            "sdk_version": 1,
            "description": "Durable user-authored offline echo workflow.",
            "inputs": [{"id": "input", "type": "string", "description": "Workflow text."}],
            "outputs": [{"id": "output", "type": "string", "description": "Workflow result."}],
            "nodes": [
                {
                    "id": "echo",
                    "operation": "ups.echo-text",
                    "inputs": [node_input],
                    "outputs": [node_output],
                }
            ],
            "edges": workflow_edges,
        },
    }


def _saved_prompt_workflow() -> dict[str, object]:
    node_inputs = [
        {
            "id": "project-id",
            "type": "string",
            "description": "Owning durable project identifier.",
        },
        {
            "id": "prompt-id",
            "type": "string",
            "description": "Durable project-owned prompt identifier.",
        },
        {
            "id": "provider-id",
            "type": "string",
            "description": "Existing host-authorized provider identifier selected for this run.",
        },
    ]
    return {
        "schema_version": 1,
        "workflow": {
            "id": "ups.saved-prompt-flow",
            "name": "Saved Prompt Flow",
            "version": "1.0.0",
            "sdk_version": 1,
            "description": "Execute one durable saved prompt through an authorized provider.",
            "inputs": [
                {"id": item["id"], "type": "string", "description": item["description"]}
                for item in node_inputs
            ],
            "outputs": [{"id": "output", "type": "string", "description": "Provider result."}],
            "nodes": [
                {
                    "id": "execute",
                    "operation": "ups.execute-saved-prompt",
                    "inputs": node_inputs,
                    "outputs": [
                        {
                            "id": "result",
                            "type": "string",
                            "description": "Bounded text returned by the authorized provider.",
                        }
                    ],
                }
            ],
            "edges": [
                {
                    "source": {"workflow_input": item["id"]},
                    "target": {"node": "execute", "port": item["id"]},
                }
                for item in node_inputs
            ]
            + [
                {
                    "source": {"node": "execute", "port": "result"},
                    "target": {"workflow_output": "output"},
                }
            ],
        },
    }


def test_operation_catalog_is_exact_and_workflow_create_plan_execute_round_trips() -> None:
    router = ApplicationIpcRouter(create_in_memory_container)

    operations = _call(router, WORKFLOW_OPERATIONS_COMMAND, {})
    created = _call(router, WORKFLOW_CREATE_COMMAND, {"workflow": _echo_workflow()})
    planned = _call(router, WORKFLOW_PLAN_COMMAND, {"workflow_id": "ups.user-echo"})
    executed = _call(
        router,
        WORKFLOW_EXECUTE_COMMAND,
        {
            "workflow_id": "ups.user-echo",
            "run_id": "550e8400-e29b-41d4-a716-446655440000",
            "inputs": [{"port_id": "input", "value": "Bounded"}],
            "confirm": True,
        },
    )

    operation_values = cast(dict[str, object], operations["result"])["operations"]
    assert [item["operation_id"] for item in operation_values] == [  # type: ignore[index]
        "ups.echo-text",
        "ups.execute-saved-prompt",
        "ups.uppercase-text",
    ]
    assert cast(dict[str, object], created["result"])["workflow"] == _echo_workflow()
    plan = cast(dict[str, object], cast(dict[str, object], planned["result"])["plan"])
    assert plan["valid"] is True
    assert plan["steps"] == [
        {
            "position": 0,
            "node_id": "echo",
            "operation_id": "ups.echo-text",
            "dependencies": [],
        }
    ]
    execution = cast(dict[str, object], cast(dict[str, object], executed["result"])["execution"])
    assert execution["succeeded"] is True
    assert execution["outputs"] == [{"port_id": "output", "value": "Bounded"}]


def test_workflow_update_and_confirmed_delete_round_trip() -> None:
    router = ApplicationIpcRouter(create_in_memory_container)
    _call(router, WORKFLOW_CREATE_COMMAND, {"workflow": _echo_workflow()})
    updated_definition = _echo_workflow()
    workflow = cast(dict[str, object], updated_definition["workflow"])
    workflow["name"] = "Updated Echo"

    updated = _call(
        router,
        WORKFLOW_UPDATE_COMMAND,
        {"workflow_id": "ups.user-echo", "workflow": updated_definition},
    )
    unconfirmed = _call(
        router,
        WORKFLOW_DELETE_COMMAND,
        {"workflow_id": "ups.user-echo", "confirm": False},
    )
    deleted = _call(
        router,
        WORKFLOW_DELETE_COMMAND,
        {"workflow_id": "ups.user-echo", "confirm": True},
    )
    listed = _call(router, WORKFLOW_LIST_COMMAND, {})

    assert cast(dict[str, object], updated["result"])["workflow"] == updated_definition
    assert cast(dict[str, object], unconfirmed["error"])["code"] == "ipc.invalid_payload"
    assert deleted["result"] == {"deleted_workflow_id": "ups.user-echo"}
    assert listed["result"] == {"workflows": [], "has_more": False}


def test_invalid_graph_is_a_durable_draft_but_cannot_execute() -> None:
    router = ApplicationIpcRouter(create_in_memory_container)
    created = _call(router, WORKFLOW_CREATE_COMMAND, {"workflow": _echo_workflow(edges=False)})
    planned = _call(router, WORKFLOW_PLAN_COMMAND, {"workflow_id": "ups.user-echo"})
    executed = _call(
        router,
        WORKFLOW_EXECUTE_COMMAND,
        {
            "workflow_id": "ups.user-echo",
            "run_id": "550e8400-e29b-41d4-a716-446655440000",
            "inputs": [{"port_id": "input", "value": "Blocked"}],
            "confirm": True,
        },
    )

    assert created["ok"] is True
    plan = cast(dict[str, object], cast(dict[str, object], planned["result"])["plan"])
    assert plan["valid"] is False
    assert plan["failures"]
    assert executed["ok"] is False
    assert cast(dict[str, object], executed["error"])["code"] == "ipc.invalid_payload"


def test_arbitrary_operations_and_missing_confirmation_are_rejected() -> None:
    arbitrary = deepcopy(_echo_workflow())
    workflow = cast(dict[str, object], arbitrary["workflow"])
    cast(list[dict[str, object]], workflow["nodes"])[0]["operation"] = "evil.dynamic-handler"
    router = ApplicationIpcRouter(create_in_memory_container)

    rejected = _call(router, WORKFLOW_CREATE_COMMAND, {"workflow": arbitrary})
    _call(router, WORKFLOW_CREATE_COMMAND, {"workflow": _echo_workflow()})
    unconfirmed = _call(
        router,
        WORKFLOW_EXECUTE_COMMAND,
        {
            "workflow_id": "ups.user-echo",
            "run_id": "550e8400-e29b-41d4-a716-446655440000",
            "inputs": [{"port_id": "input", "value": "No"}],
            "confirm": False,
        },
    )

    assert cast(dict[str, object], rejected["error"])["code"] == "ipc.invalid_payload"
    assert cast(dict[str, object], unconfirmed["error"])["code"] == "ipc.invalid_payload"


def test_saved_prompt_operation_reuses_offline_provider_without_embedded_credentials() -> None:
    container = create_in_memory_container()
    project = container.project_service.create_project("Workflow project")
    prompt = container.prompt_service.create_library_prompt(project.project_id, "Workflow prompt")
    container.prompt_service.update_library_prompt(
        project.project_id,
        prompt.prompt_id,
        prompt.title,
        None,
        (),
        (PromptBlock(PromptBlockType.GOAL, "Ship safely", 0),),
    )
    router = ApplicationIpcRouter(lambda: container)
    definition = _saved_prompt_workflow()
    assert "credential" not in repr(definition).lower()
    _call(router, WORKFLOW_CREATE_COMMAND, {"workflow": definition})

    result = _call(
        router,
        WORKFLOW_EXECUTE_COMMAND,
        {
            "workflow_id": "ups.saved-prompt-flow",
            "run_id": "76c7169d-9e5d-4db4-bf61-856695d2a91e",
            "inputs": [
                {"port_id": "project-id", "value": project.project_id},
                {"port_id": "prompt-id", "value": prompt.prompt_id},
                {"port_id": "provider-id", "value": "ups.offline-echo"},
            ],
            "confirm": True,
        },
    )

    execution = cast(dict[str, object], cast(dict[str, object], result["result"])["execution"])
    assert execution["succeeded"] is True
    assert "Ship safely" in repr(execution["outputs"])


def test_workflow_definitions_persist_outside_sqlite_and_invalid_store_is_safe(
    tmp_path: Path,
) -> None:
    database = tmp_path / DATABASE_FILE_NAME
    first_container = create_sqlite_container(database)
    first_router = ApplicationIpcRouter(lambda: first_container)
    _call(first_router, WORKFLOW_CREATE_COMMAND, {"workflow": _echo_workflow()})

    second_router = ApplicationIpcRouter(lambda: create_sqlite_container(database))
    listed = _call(second_router, WORKFLOW_LIST_COMMAND, {})
    fetched = _call(
        second_router,
        WORKFLOW_GET_COMMAND,
        {"workflow_id": "ups.user-echo"},
    )

    assert cast(dict[str, object], listed["result"])["workflows"]
    assert cast(dict[str, object], fetched["result"])["workflow"] == _echo_workflow()
    assert CURRENT_SCHEMA_VERSION == 1
    store = tmp_path / WORKFLOW_DEFINITIONS_FILE_NAME
    assert store.is_file()
    store.write_text('{"schema_version":1,"workflows":[{"operation":"dynamic"}]}')

    invalid_router = ApplicationIpcRouter(lambda: create_sqlite_container(database))
    invalid = _call(invalid_router, WORKFLOW_LIST_COMMAND, {})
    assert cast(dict[str, object], invalid["error"])["code"] == "workflow.storage_invalid"
    assert "dynamic" not in repr(invalid)
