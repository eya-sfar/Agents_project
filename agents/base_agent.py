"""
agents/base_agent.py
Abstract base class for all MAS agents.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict
from utils.logger import logger
from database.connection import get_session
from database.models import AgentRun


class BaseAgent(ABC):
    """
    All agents inherit from this class.
    Provides lifecycle management and audit logging.
    """

    def __init__(self, name: str):
        self.name = name
        self.run_id: str = None
        self._records = 0
        logger.info(f"[{self.name}] Initialized")

    # ── Lifecycle ──────────────────────────────────────────────
    def start(self, **kwargs) -> Any:
        """Public entry point — logs the run then calls run()."""
        self._log_start()
        try:
            result = self.run(**kwargs)
            self._log_finish(success=True)
            return result
        except Exception as e:
            self._log_finish(success=False, error=str(e))
            raise

    @abstractmethod
    def run(self, **kwargs) -> Any:
        """Override in each agent. Contains the core agent logic."""
        ...

    # ── Messaging (simple publish/subscribe stub) ─────────────
    def send_message(self, recipient_agent: "BaseAgent", message: Dict):
        """Dispatch a message to another agent directly (synchronous MAS)."""
        logger.debug(f"[{self.name}] → [{recipient_agent.name}]: {list(message.keys())}")
        return recipient_agent.receive_message(sender=self.name, message=message)

    def receive_message(self, sender: str, message: Dict) -> Any:
        """Override to handle incoming messages from other agents."""
        logger.debug(f"[{self.name}] received message from [{sender}]")
        return None

    # ── Audit helpers ─────────────────────────────────────────
    def _log_start(self):
        with get_session() as session:
            run = AgentRun(agent_name=self.name, status="started")
            session.add(run)
            session.flush()
            self.run_id = run.run_id
        logger.info(f"[{self.name}] Run started (id={self.run_id})")

    def _log_finish(self, success: bool, error: str = None):
        with get_session() as session:
            run = session.query(AgentRun).filter_by(run_id=self.run_id).first()
            if run:
                run.status = "completed" if success else "failed"
                run.records_processed = self._records
                run.error_message = error
                run.finished_at = datetime.utcnow()
        status = "completed" if success else f"FAILED ({error})"
        logger.info(f"[{self.name}] Run {status} — {self._records} records processed")

    def _increment(self, count: int = 1):
        self._records += count