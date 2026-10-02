"""One typed CLI packet selected by the existing V2 model routing workflow.

No retry loop, quality grading, policy adoption, credential reads, or promotion.
The parent owns diagnostics, correction lineage, review, and task completion.
"""
from __future__ import annotations

import pathlib
import sys

import agent_routing
import profile_preflight
import model_packet_store


class ExecutionContractError(ValueError):
    pass


def _packet_store(binding, validated, task, adapter):
    stable = {'repository': adapter._canonical_repository_id(validated.workspace),
              'task_id': task['id'], 'scope': task['qualification_scope'],
              'acceptance_sha256': binding.acceptance_sha256}
    packet_id = model_packet_store.digest(model_packet_store.canonical(stable))
    packet = model_packet_store.PacketStore(binding.root/'model-packets', packet_id)
    # Same objective cannot silently adopt a new source HEAD or a different
    # packet directory to evade an unknown previous attempt.
    packet.prepare(model_packet_store.digest(model_packet_store.canonical({**stable, 'source_head': validated.expected_head})))
    return packet


def _cli_adapter():
    # Source, plugin and filesystem installs retain the sibling skill layout.
    directory = pathlib.Path(__file__).resolve().parents[2] / 'cli-session-handoff' / 'scripts'
    if not (directory / 'cli_session_handoff.py').is_file():
        raise ExecutionContractError('qualified-cli-adapter-unavailable')
    sys.path.insert(0, str(directory))
    try:
        import cli_session_handoff
        import model_execution_target
    except ImportError:
        raise ExecutionContractError('qualified-cli-adapter-unavailable') from None
    finally:
        sys.path.pop(0)
    if pathlib.Path(cli_session_handoff.__file__).resolve() != (directory / 'cli_session_handoff.py').resolve():
        raise ExecutionContractError('cli-adapter-origin-mismatch')
    if pathlib.Path(model_execution_target.__file__).resolve() != (directory / 'model_execution_target.py').resolve():
        raise ExecutionContractError('cli-target-loader-origin-mismatch')
    return cli_session_handoff, model_execution_target


def execute_next(task, failover_input, cli_request):
    """Validate a shared plan against protected target bytes, then one dispatch.

    A process/session result is not model/provider readback or task completion.
    No failed request is automatically repeated, nor are review gates weakened.
    """
    planned = agent_routing.plan_model_failover(task, failover_input)
    plan = planned['plan']
    output = {**planned, 'execution': None, 'repository_completion_claimed': False}
    if plan['status'] not in {'planned', 'retry'}:
        return output
    if not isinstance(cli_request, dict) or cli_request.get('operation') != 'start' or 'target_ref' not in cli_request:
        raise ExecutionContractError('typed-cli-start-required')
    selected = plan['target']
    if selected['identity']['runtime'] != 'cli':
        raise ExecutionContractError('selected-target-requires-another-public-adapter')
    adapter, target_loader = _cli_adapter()
    if not adapter.PACKET_STOP_ADAPTERS:
        raise ExecutionContractError('qualified-packet-writer-containment-unavailable')
    try:
        validated = adapter.validate_request(cli_request)
    except adapter.HandoffValidationError as exc:
        raise ExecutionContractError('cli-target-preflight-rejected:' + exc.failure_class) from None
    binding = validated.execution_target
    if binding is None or binding.target_id != selected['id']:
        raise ExecutionContractError('selected-target-binding-mismatch')
    if target_loader.target_identity(binding) != selected['identity']:
        raise ExecutionContractError('selected-target-identity-mismatch')
    expected = (task['id'], task['qualification_scope'], failover_input['task']['acceptance_sha256'])
    actual = (binding.task_id, binding.scope, binding.acceptance_sha256)
    if actual != expected:
        raise ExecutionContractError('selected-target-task-contract-mismatch')
    # A qualified higher tier of the same class is valid. Requiring the initial
    # selected_role would silently prevent the existing capability escalation.
    entries = [entry for entry in profile_preflight.load_registry(profile_preflight.DEFAULT_REGISTRY)['profiles']
               if entry['name'] == binding.role]
    classification = planned['classification']
    if (len(entries) != 1 or entries[0]['capability_class'] != classification['capability_class']
            or profile_preflight.TIER_RANK[entries[0]['capability_tier']] < profile_preflight.TIER_RANK[classification['capability_tier']]
            or (entries[0]['capability_tier'] == 'exceptional' and classification['capability_tier'] != 'exceptional')):
        raise ExecutionContractError('selected-target-role-contract-mismatch')
    # A qualified registry entry must explicitly support this exact protected
    # target/host contract. Registration order cannot choose an executor.
    matches = [name for name, candidate in adapter.PACKET_STOP_ADAPTERS.items()
               if callable(getattr(candidate, 'supports_target', None))
               and candidate.supports_target(binding) is True]
    if len(matches) != 1:
        raise ExecutionContractError('qualified-packet-containment-binding-ambiguous')
    stop_adapter_id = matches[0]
    # The executor repeats its own preflight and launch-boundary readback. Its
    # fixed target reference binds the same store/record bytes across both calls.
    def unknown():
        return {**output, 'dispatched': None,
                'execution': {'status': 'unknown', 'failure_class': 'cli-execution-outcome-unknown',
                              'independent_readback_required': True}}

    try:
        packet = _packet_store(binding, validated, task, adapter)
        ledger, _ = packet.read_checkpoint()
        attempt_id = model_packet_store.digest(model_packet_store.canonical(cli_request))
        receipt = adapter.execute_packet_attempt(cli_request, packet, attempt_id, ledger['revision'],
            stop_adapter_id=stop_adapter_id)
        if not isinstance(receipt, dict) or receipt.get('status') not in {'completed', 'stopped', 'failed', 'unknown'}:
            return unknown()
        performed = receipt['boundaries']['session_call_performed']
        if type(performed) is not bool or receipt['boundaries']['repository_completion_claimed'] is not False:
            return unknown()
        if performed:
            returned_target = receipt['execution_target']
            if returned_target['id'] != binding.target_id or returned_target['binding_sha256'] != binding.binding_sha256:
                return unknown()
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        # A consumer fault after entering the executor cannot prove that no
        # session or tool call occurred. Never turn uncertainty into a retry.
        return unknown()
    output['execution'] = receipt
    output['dispatched'] = performed
    return output
