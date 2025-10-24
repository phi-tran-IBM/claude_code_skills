"""
MEA (Mandatory Execution Algorithm) Orchestration Package

Provides full Write → Validate → Fix → Repeat loop implementation
for the SCA Protocol Skill tool.
"""

from .orchestrator import MEAOrchestrator
from .failure_parser import FailureParser
from .fix_generator import FixGenerator
from .state_manager import MEAStateManager

__all__ = [
    'MEAOrchestrator',
    'FailureParser',
    'FixGenerator',
    'MEAStateManager'
]

__version__ = '1.0.0'