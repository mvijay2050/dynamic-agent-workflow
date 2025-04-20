from abc import ABC, abstractmethod

class BaseTask(ABC):
    """All tasks implement `key`, `name`, and `run(input_text)`."""

    @property
    @abstractmethod
    def key(self) -> str:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def run(self, input_text: str) -> dict:
        """
        Executes the task.
        :param input_text: Tibco code/config.
        :return: JSON-serializable dict.
        """
        ...
