from abc import ABC, abstractmethod


class BaseIngestionClient(ABC):
    @abstractmethod
    async def fetch(self, *args, **kwargs):
        raise NotImplementedError
