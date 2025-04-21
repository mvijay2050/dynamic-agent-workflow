from abc import ABC, abstractmethod

class BaseTask(ABC):
    """All tasks must define `key`, `name`, `supported_techs`, and implement `run(input_text)`."""

    @property
    @abstractmethod
    def key(self) -> str:
        """Unique identifier for the task."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human‑readable name for display in the UI."""
        ...

    # New: restrict each task to one or more source technologies
    supported_techs: list[str] = []

    @abstractmethod
    def run(self, code: str) -> dict:
        """
        Executes the task for the given source code.
        :param code: Source code or configuration for the selected technology.
        :return: JSON‑serializable dict of results.
        """
        ...