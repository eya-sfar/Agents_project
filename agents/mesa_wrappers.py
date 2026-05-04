"""
agents/mesa_wrappers.py

Wrappeurs Mesa pour les agents d'analyse (non-scrapers).
Ils convertissent nos BaseAgent en mesa.Agent
en déléguant step() → agent.start().
"""
from typing import Dict
import mesa

from utils.logger import logger


class _WrappedMesaAgent(mesa.Agent):
    """Base wrapper : délègue step() à un BaseAgent existant."""

    _agent_class = None   # à définir dans les sous-classes

    def __init__(self, model: mesa.Model, **kwargs):
        super().__init__(model)
        self._inner = self._agent_class()
        self._kwargs = kwargs

    def step(self):
        result = self._inner.start(**self._kwargs)
        self.model.on_agent_done(self._inner.name, result or {})


class AgentExpertiseMatcherMesa(_WrappedMesaAgent):
    @property
    def _agent_class(self):
        from agents.agent_expertise_matcher import AgentExpertiseMatcher
        return AgentExpertiseMatcher

    def __init__(self, model):
        mesa.Agent.__init__(self, model)
        from agents.agent_expertise_matcher import AgentExpertiseMatcher
        self._inner = AgentExpertiseMatcher()

    def step(self):
        result = self._inner.start()
        self.model.on_agent_done(self._inner.name, result or {})


class AgentClusterMesa(_WrappedMesaAgent):
    def __init__(self, model, n_clusters: int = 8):
        mesa.Agent.__init__(self, model)
        from agents.agent_cluster import AgentCluster
        self._inner = AgentCluster()
        self._n_clusters = n_clusters

    def step(self):
        result = self._inner.start(n_clusters=self._n_clusters)
        self.model.on_agent_done(self._inner.name, result or {})


class AgentCollabAdvisorMesa(_WrappedMesaAgent):
    def __init__(self, model):
        mesa.Agent.__init__(self, model)
        from agents.agent_collab_advisor import AgentCollabAdvisor
        self._inner = AgentCollabAdvisor()

    def step(self):
        result = self._inner.start()
        self.model.on_agent_done(self._inner.name, result or {})


class AgentNegotiatorMesa(_WrappedMesaAgent):
    def __init__(self, model):
        mesa.Agent.__init__(self, model)
        from agents.agent_negotiator import AgentNegotiator
        self._inner = AgentNegotiator()

    def step(self):
        result = self._inner.start()
        self.model.on_agent_done(self._inner.name, result or {})
