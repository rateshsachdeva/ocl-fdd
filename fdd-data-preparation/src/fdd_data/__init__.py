"""AI-understanding + deterministic-Python FDD data-preparation runtime."""

from .dataset_map import DatasetMapValidationError, validate_dataset_map, validate_dataset_map_file
from .executor import UnsupportedOperationError, execute_processing_plan
from .inspection import InspectionError, inspect_source
from .orchestration import WORKFLOW_STATES, WorkflowError, get_databook_status, record_workflow_user_decisions, run_databook, source_fingerprint
from .processing_plan import ApprovalError, ExecutionNotApprovedError, ProcessingPlanValidationError, SourceIntegrityError, approve_plan, build_source_snapshot, compute_plan_hash, prepare_plan, validate_processing_plan
from .profiler import profile_directory, profile_source_file, profile_source_files

__all__ = [
    "ApprovalError", "DatasetMapValidationError", "ExecutionNotApprovedError", "InspectionError",
    "ProcessingPlanValidationError", "SourceIntegrityError", "UnsupportedOperationError", "WORKFLOW_STATES",
    "WorkflowError", "approve_plan", "build_source_snapshot", "compute_plan_hash", "execute_processing_plan",
    "get_databook_status", "inspect_source", "prepare_plan", "profile_directory", "profile_source_file",
    "profile_source_files", "record_workflow_user_decisions", "run_databook", "source_fingerprint",
    "validate_dataset_map", "validate_dataset_map_file", "validate_processing_plan",
]
