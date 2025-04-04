from contextlib import asynccontextmanager
from typing import AsyncIterator
import logging
from fastapi import FastAPI

logger = logging.getLogger(__name__)

class LifecycleManager:
    def __init__(self):
        self._resources = []
        
    def add_resource(self, name: str, startup: callable, shutdown: callable):
        """Register a resource with lifecycle methods"""
        self._resources.append({
            'name': name,
            'startup': startup,
            'shutdown': shutdown
        })
    
    @asynccontextmanager
    async def lifespan(self, app: FastAPI) -> AsyncIterator[None]:
        """The main lifespan context manager"""
        logger.info("Starting application lifecycle")
        
        # Startup all registered resources
        for resource in self._resources:
            try:
                logger.debug(f"Starting {resource['name']}")
                await resource['startup']()
            except Exception as e:
                logger.error(f"Failed to start {resource['name']}: {str(e)}")
                raise
        
        yield
        
        # Shutdown all registered resources in reverse order
        for resource in reversed(self._resources):
            try:
                logger.debug(f"Shutting down {resource['name']}")
                await resource['shutdown']()
            except Exception as e:
                logger.error(f"Failed to shutdown {resource['name']}: {str(e)}")

        logger.info("Stopping application lifecycle")

# Global lifecycle manager instance
lifecycle = LifecycleManager()
