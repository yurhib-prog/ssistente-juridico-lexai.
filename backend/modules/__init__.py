# LexAI - Assistente Jurídico com IA
# Módulos do sistema

from .chunking import ChunkingJuridico
from .entities import EntityExtractor
from .search import HybridSearch
from .reranking import Reranker
from .grammar import GrammarCorrector
from .assistant import JuridicAssistant

__all__ = [
    'ChunkingJuridico',
    'EntityExtractor', 
    'HybridSearch',
    'Reranker',
    'GrammarCorrector',
    'JuridicAssistant'
]
