"""
Core Module - Auto-generación, Registry, Context Manager y Process Manager v4.4
"""

from core.module_registry import (
    module_registry,
    module_generator,
    ModuleRegistry,
    ModuleGenerator,
    get_registry_info,
    generate_module_code
)

from core.context_manager import (
    CaseContextManager,
    CaseContext,
    case_context_manager,
    get_case_context
)

from core.process_manager import (
    ProcessManager,
    ForensicProcess,
    ProcessStatus,
    ProcessType,
    process_manager,
    get_process_manager
)

__all__ = [
    "module_registry",
    "module_generator",
    "ModuleRegistry",
    "ModuleGenerator",
    "get_registry_info",
    "generate_module_code",
    # v4.4 Context Manager
    "CaseContextManager",
    "CaseContext",
    "case_context_manager",
    "get_case_context",
    # v4.4 Process Manager
    "ProcessManager",
    "ForensicProcess",
    "ProcessStatus",
    "ProcessType",
    "process_manager",
    "get_process_manager"
]

