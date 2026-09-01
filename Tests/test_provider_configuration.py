"""A-004 provider settings, credential, execution, and redaction tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import cast

import pytest

from Backend.application.provider_settings import (
    OPENAI_CREDENTIAL_REFERENCE,
    OPENAI_RESPONSES_ENDPOINT,
    OPENAI_RESPONSES_PROVIDER,
    OPENAI_RESPONSES_VERSION,
    InMemoryProviderSettingsRepository,
    InMemorySecretStore,
    JsonProviderSettingsRepository,
    ProviderConfigurationService,
    ProviderSettings,
    ProviderUnavailableError,
)
from Backend.core.container import create_in_memory_container
from Backend.infrastructure.providers import (
    OpenAIResponsesProvider,
    WindowsDpapiSecretStore,
    openai_responses_provider_record,
)
from Backend.ipc.models import IPC_PROTOCOL_VERSION, IpcRequest
from Backend.ipc.router import (
    PROMPT_EXECUTE_CONFIGURED_COMMAND,
    PROVIDER_CATALOG_COMMAND,
    PROVIDER_CREDENTIAL_CLEAR_COMMAND,
    PROVIDER_SETTINGS_SAVE_COMMAND,
    ApplicationIpcRouter,
)

SECRET = "sk-test-a004-never-disclose"


def _configured_service() -> ProviderConfigurationService:
    service = ProviderConfigurationService(
        InMemoryProviderSettingsRepository(), InMemorySecretStore()
    )
    service.save(
        OPENAI_RESPONSES_PROVIDER,
        OPENAI_RESPONSES_ENDPOINT,
        "gpt-5-mini",
        0.5,
        256,
        SECRET,
    )
    return service


def test_configuration_catalog_never_returns_secret_and_clear_disables_provider() -> None:
    service = _configured_service()
    offline, remote = service.catalog()

    assert offline.available and offline.credential_state == "not-required"
    assert remote.available and remote.credential_state == "stored"
    assert remote.credential_reference == OPENAI_CREDENTIAL_REFERENCE
    assert SECRET not in repr((offline, remote))

    cleared = service.clear_credential(OPENAI_RESPONSES_PROVIDER)
    assert not cleared.available
    assert cleared.credential_state == "missing"
    with pytest.raises(ProviderUnavailableError):
        service.require_execution_settings(OPENAI_RESPONSES_PROVIDER)


def test_non_secret_json_settings_are_exact_atomic_and_secret_free(tmp_path: Path) -> None:
    path = tmp_path / "provider-settings.json"
    repository = JsonProviderSettingsRepository(path)
    settings = ProviderSettings(model="gpt-5-mini", temperature=0.25, max_output_tokens=512)
    repository.save(settings)

    assert repository.get() == settings
    raw = path.read_text(encoding="utf-8")
    assert SECRET not in raw
    assert set(json.loads(raw)) == {"schema_version", "settings"}
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI is Windows-only")
def test_windows_dpapi_round_trip_never_writes_plaintext(tmp_path: Path) -> None:
    store = WindowsDpapiSecretStore(tmp_path / "credentials")
    store.set(OPENAI_CREDENTIAL_REFERENCE, SECRET)

    files = list((tmp_path / "credentials").glob("*.dpapi"))
    assert len(files) == 1
    assert SECRET.encode() not in files[0].read_bytes()
    assert store.get(OPENAI_CREDENTIAL_REFERENCE) == SECRET
    assert store.delete(OPENAI_CREDENTIAL_REFERENCE)
    assert not store.contains(OPENAI_CREDENTIAL_REFERENCE)


def test_host_provider_uses_only_saved_schema_and_returns_bounded_result() -> None:
    captured: dict[str, object] = {}

    def transport(endpoint: str, credential: str, payload: dict[str, object]) -> dict[str, object]:
        captured.update(endpoint=endpoint, credential=credential, payload=payload)
        return {
            "model": "gpt-5-mini-2026-08-01",
            "output_text": "Configured response",
            "usage": {"input_tokens": 4, "output_tokens": 2},
        }

    service = _configured_service()
    provider = OpenAIResponsesProvider(service, transport)
    from Engineering.ProviderSystem import ProviderRequestOption, ProviderTextRequest

    result = provider.generate_text(
        ProviderTextRequest(
            "request-1",
            "Compose safely",
            "gpt-5-mini",
            (
                ProviderRequestOption("temperature", 0.5),
                ProviderRequestOption("max-output-tokens", 256),
            ),
        )
    )

    assert result.text == "Configured response"  # type: ignore[union-attr]
    assert captured["endpoint"] == OPENAI_RESPONSES_ENDPOINT
    assert captured["credential"] == SECRET
    assert cast(dict[str, object], captured["payload"])["store"] is False
    assert SECRET not in repr(result)


def test_saved_prompt_executes_through_registered_configured_provider() -> None:
    container = create_in_memory_container()
    service = container.provider_configuration_service
    service.save(
        OPENAI_RESPONSES_PROVIDER,
        OPENAI_RESPONSES_ENDPOINT,
        "gpt-5-mini",
        1.0,
        128,
        SECRET,
    )
    container.provider_runtime_registry.unregister(
        OPENAI_RESPONSES_PROVIDER, OPENAI_RESPONSES_VERSION
    )
    container.provider_runtime_registry.register(
        openai_responses_provider_record(),
        OpenAIResponsesProvider(
            service,
            lambda _endpoint, _credential, _payload: {
                "model": "gpt-5-mini",
                "output_text": "Remote result",
                "usage": {"input_tokens": 3, "output_tokens": 2},
            },
        ),
    )
    project = container.project_service.create_project("Provider project")
    prompt = container.prompt_service.create_library_prompt(project.project_id, "Configured")
    from Backend.domain.models import PromptBlock, PromptBlockType

    container.prompt_service.update_library_prompt(
        project.project_id,
        prompt.prompt_id,
        prompt.title,
        None,
        (),
        (PromptBlock(PromptBlockType.GOAL, "Ship safely", 0),),
    )

    composition, result = container.saved_prompt_runtime_service.execute_configured(
        project.project_id, prompt.prompt_id, OPENAI_RESPONSES_PROVIDER
    )
    assert composition.final_prompt == "Goal:\nShip safely"
    assert result.output == "Remote result"
    assert result.metadata["model"] == "gpt-5-mini"
    assert SECRET not in repr(result)


def test_provider_ipc_catalog_save_clear_and_safe_unavailable_execution() -> None:
    router = ApplicationIpcRouter(create_in_memory_container)

    def call(command: str, payload: dict[str, object]) -> dict[str, object]:
        response = router.handle(
            IpcRequest(IPC_PROTOCOL_VERSION, f"request-{command}", command, payload)  # type: ignore[arg-type]
        ).to_dict()
        return cast(dict[str, object], response)

    catalog = call(PROVIDER_CATALOG_COMMAND, {})
    assert catalog["ok"] is True
    assert SECRET not in repr(catalog)

    saved = call(
        PROVIDER_SETTINGS_SAVE_COMMAND,
        {
            "provider_id": OPENAI_RESPONSES_PROVIDER,
            "endpoint": OPENAI_RESPONSES_ENDPOINT,
            "model": "gpt-5-mini",
            "temperature": 1.0,
            "max_output_tokens": 512,
            "credential": SECRET,
        },
    )
    assert saved["ok"] is True
    assert SECRET not in repr(saved)

    cleared = call(
        PROVIDER_CREDENTIAL_CLEAR_COMMAND,
        {"provider_id": OPENAI_RESPONSES_PROVIDER, "confirm": True},
    )
    assert cleared["ok"] is True
    failed = call(
        PROMPT_EXECUTE_CONFIGURED_COMMAND,
        {
            "project_id": "550e8400-e29b-41d4-a716-446655440000",
            "prompt_id": "76c7169d-9e5d-4db4-bf61-856695d2a91e",
            "provider_id": OPENAI_RESPONSES_PROVIDER,
            "confirm": True,
        },
    )
    assert failed["ok"] is False
    assert cast(dict[str, object], failed["error"])["code"] == "provider.unavailable"
    assert SECRET not in repr(failed)


@pytest.mark.parametrize(
    "settings",
    [
        {"endpoint": "http://api.openai.com/v1/responses"},
        {"endpoint": "https://evil.example/v1/responses"},
        {"model": "bad model"},
        {"temperature": 2.1},
        {"max_output_tokens": 0},
    ],
)
def test_settings_reject_unapproved_or_unbounded_values(settings: dict[str, object]) -> None:
    values: dict[str, object] = {
        "endpoint": OPENAI_RESPONSES_ENDPOINT,
        "model": "gpt-5-mini",
        "temperature": 1.0,
        "max_output_tokens": 512,
    }
    values.update(settings)
    with pytest.raises(ValueError):
        ProviderSettings(
            endpoint=cast(str, values["endpoint"]),
            model=cast(str, values["model"]),
            temperature=cast(float, values["temperature"]),
            max_output_tokens=cast(int, values["max_output_tokens"]),
        )
