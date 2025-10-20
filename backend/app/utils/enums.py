from enum import Enum


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RERENDERING = "rerendering"
    NOT_REQUESTED = "not_requested"
