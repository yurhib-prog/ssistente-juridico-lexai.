"""
HybridSearch — Módulo de Busca Híbrida (BM25 + Embedding Denso)

Combina busca léxica (BM25) com busca semântica (embeddings densos)
para recuperação de documentos jurídicos com alta precisão.
"""

import re
import math
import numpy as np
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional


@dataclass
class DocumentoIndexado:
    """Documento indexado para busca."""
    id: str
    conteudo: str
    tokens: List[str] = field(default_factory=list)
    embedding: Optional[np.ndarray] = None
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "conteudo": self.conteudo[:200],
            "metadata": self.metadata,
            "num_tokens": len(self.tokens)
        }


@dataclass 
class ResultadoBusca:
    """Resultado de uma busca com score combinado."""
    documento: DocumentoIndexado
    score_bm25: float = 0.0
    score_semantico: float = 0.0
    score_combinado: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "id": self.documento.id,
            "conteudo": self.documento.conteudo,
            "score_bm25": round(self.score_bm25, 4),
            "score_semantico": round(self.score_semantico, 4),
            "score_combinado": round(self.score_combinado, 4),
            "metadata": self.documento.metadata
        }


class BM25:
    """
    Implementação do algoritmo BM25 (Okapi BM25) para busca léxica.
    Otimizado para termos jurídicos em português.
    """
    
    # Stopwords jurídicas em português
    STOPWORDS_PT = {
        "a", "o", "e", "é", "de", "do", "da", "dos", "das", "em", "no", "na",
        "nos", "nas", "um", "uma", "uns", "umas", "por", "para", "com", "sem",
        "sob", "sobre", "entre", "contra", "após", "até", "desde", "que",
        "se", "ao", "aos", "à", "às", "ou", "como", "mais", "menos", "muito",
        "já", "ainda", "também", "mas", "porém", "contudo", "todavia",
        "não", "nem", "ser", "ter", "haver", "estar", "ir", "vir", "fazer",
        "este", "esta", "esse", "essa", "aquele", "aquela", "isto", "isso",
        "aquilo", "seu", "sua", "seus", "suas", "meu", "minha", "nosso", "nossa",
        "foi", "são", "será", "seria", "pode", "deve", "deverá", "poderá",
    }
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Args:
            k1: Parâmetro de saturação de frequência (1.2-2.0).
            b: Parâmetro de normalização por comprimento (0.75 padrão).
        """
        self.k1 = k1
        self.b = b
        self.corpus: List[List[str]] = []
        self.doc_freq: Dict[str, int] = {}
        self.doc_len: List[int] = []
        self.avg_dl: float = 0.0
        self.n_docs: int = 0
        self.idf_cache: Dict[str, float] = {}
    
    def tokenize(self, texto: str) -> List[str]:
        """Tokeniza texto removendo stopwords e normalizando."""
        texto = texto.lower()
        texto = re.sub(r'[^\w\sáàâãéèêíìîóòôõúùûçü]', ' ', texto)
        tokens = texto.split()
        tokens = [t for t in tokens if t not in self.STOPWORDS_PT and len(t) > 1]
        return tokens
    
    def fit(self, documentos: List[str]) -> None:
        """Indexa uma lista de documentos para busca BM25."""
        self.corpus = [self.tokenize(doc) for doc in documentos]
        self.n_docs = len(self.corpus)
        self.doc_len = [len(doc) for doc in self.corpus]
        self.avg_dl = sum(self.doc_len) / self.n_docs if self.n_docs > 0 else 0
        
        # Calcular frequência de documento para cada termo
        self.doc_freq = {}
        for doc_tokens in self.corpus:
            termos_unicos = set(doc_tokens)
            for termo in termos_unicos:
                self.doc_freq[termo] = self.doc_freq.get(termo, 0) + 1
        
        # Pré-calcular IDF
        self.idf_cache = {}
        for termo, df in self.doc_freq.items():
            self.idf_cache[termo] = math.log(
                (self.n_docs - df + 0.5) / (df + 0.5) + 1.0
            )
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """
        Busca documentos mais relevantes para a query.
        
        Returns:
            Lista de tuplas (índice_documento, score_bm25).
        """
        query_tokens = self.tokenize(query)
        scores = []
        
        for i, doc_tokens in enumerate(self.corpus):
            score = self._score_document(query_tokens, doc_tokens, self.doc_len[i])
            scores.append((i, score))
        
        scores.sort(key=lambda x: -x[1])
        return scores[:top_k]
    
    def _score_document(
        self, query_tokens: List[str], doc_tokens: List[str], doc_len: int
    ) -> float:
        """Calcula o score BM25 de um documento para a query."""
        tf = Counter(doc_tokens)
        score = 0.0
        
        for term in query_tokens:
            if term not in tf:
                continue
            
            idf = self.idf_cache.get(term, 0)
            term_freq = tf[term]
            
            numerator = term_freq * (self.k1 + 1)
            denominator = term_freq + self.k1 * (
                1 - self.b + self.b * doc_len / self.avg_dl
            )
            
            score += idf * numerator / denominator
        
        return score


class SimpleEmbedding:
    """
    Embedding simples baseado em TF-IDF para demonstração.
    Em produção, usar sentence-transformers com modelo multilingual.
    """
    
    def __init__(self, dim: int = 128):
        self.dim = dim
        self.vocabulary: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self._fitted = False
    
    def fit(self, textos: List[str]) -> None:
        """Constrói vocabulário e calcula IDF."""
        tokenizer = BM25()
        all_tokens = set()
        doc_tokens = []
        
        for texto in textos:
            tokens = tokenizer.tokenize(texto)
            doc_tokens.append(tokens)
            all_tokens.update(tokens)
        
        # Criar vocabulário (limitar ao dim)
        token_freq = Counter()
        for tokens in doc_tokens:
            token_freq.update(set(tokens))
        
        most_common = token_freq.most_common(self.dim)
        self.vocabulary = {token: i for i, (token, _) in enumerate(most_common)}
        
        # Calcular IDF
        n_docs = len(textos)
        for token, idx in self.vocabulary.items():
            df = token_freq.get(token, 0)
            self.idf[token] = math.log((n_docs + 1) / (df + 1)) + 1.0
        
        self._fitted = True
    
    def encode(self, texto: str) -> np.ndarray:
        """Gera embedding para um texto."""
        tokenizer = BM25()
        tokens = tokenizer.tokenize(texto)
        tf = Counter(tokens)
        
        embedding = np.zeros(self.dim)
        for token, count in tf.items():
            if token in self.vocabulary:
                idx = self.vocabulary[token]
                embedding[idx] = count * self.idf.get(token, 1.0)
        
        # Normalizar (L2)
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding
    
    def similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Calcula similaridade cosseno entre dois embeddings."""
        dot = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot / (norm1 * norm2))


class HybridSearch:
    """
    Busca Híbrida combinando BM25 (léxica) com embedding denso (semântica).
    
    Utiliza Reciprocal Rank Fusion (RRF) para combinar os rankings
    de ambos os métodos de busca.
    """
    
    def __init__(
        self, 
        alpha: float = 0.5, 
        rrf_k: int = 60,
        embedding_dim: int = 128
    ):
        """
        Args:
            alpha: Peso da busca semântica vs léxica (0=BM25, 1=semântica).
            rrf_k: Parâmetro k do Reciprocal Rank Fusion.
            embedding_dim: Dimensão dos embeddings.
        """
        self.alpha = alpha
        self.rrf_k = rrf_k
        self.bm25 = BM25()
        self.embedder = SimpleEmbedding(dim=embedding_dim)
        self.documentos: List[DocumentoIndexado] = []
        self._indexado = False
    
    def indexar(self, documentos: List[Dict[str, str]]) -> int:
        """
        Indexa uma lista de documentos.
        
        Args:
            documentos: Lista de dicts com 'id', 'conteudo', e opcionalmente 'metadata'.
            
        Returns:
            Número de documentos indexados.
        """
        conteudos = [doc.get("conteudo", "") for doc in documentos]
        
        # Indexar BM25
        self.bm25.fit(conteudos)
        
        # Gerar embeddings
        self.embedder.fit(conteudos)
        
        # Criar documentos indexados
        self.documentos = []
        for doc in documentos:
            conteudo = doc.get("conteudo", "")
            doc_indexado = DocumentoIndexado(
                id=doc.get("id", ""),
                conteudo=conteudo,
                tokens=self.bm25.tokenize(conteudo),
                embedding=self.embedder.encode(conteudo),
                metadata=doc.get("metadata", {})
            )
            self.documentos.append(doc_indexado)
        
        self._indexado = True
        return len(self.documentos)
    
    def buscar(
        self, 
        query: str, 
        top_k: int = 10, 
        metodo: str = "hibrido"
    ) -> List[ResultadoBusca]:
        """
        Busca documentos relevantes para a query.
        
        Args:
            query: Consulta em linguagem natural.
            top_k: Número de resultados a retornar.
            metodo: "bm25", "semantico", ou "hibrido".
            
        Returns:
            Lista de ResultadoBusca ordenados por relevância.
        """
        if not self._indexado:
            raise ValueError("Índice não construído. Chame indexar() primeiro.")
        
        if metodo == "bm25":
            return self._busca_bm25(query, top_k)
        elif metodo == "semantico":
            return self._busca_semantica(query, top_k)
        else:
            return self._busca_hibrida(query, top_k)
    
    def _busca_bm25(self, query: str, top_k: int) -> List[ResultadoBusca]:
        """Busca usando apenas BM25."""
        resultados_bm25 = self.bm25.search(query, top_k)
        
        resultados = []
        for idx, score in resultados_bm25:
            if score > 0:
                resultados.append(ResultadoBusca(
                    documento=self.documentos[idx],
                    score_bm25=score,
                    score_combinado=score
                ))
        
        return resultados
    
    def _busca_semantica(self, query: str, top_k: int) -> List[ResultadoBusca]:
        """Busca usando apenas embeddings."""
        query_emb = self.embedder.encode(query)
        
        scores = []
        for i, doc in enumerate(self.documentos):
            if doc.embedding is not None:
                sim = self.embedder.similarity(query_emb, doc.embedding)
                scores.append((i, sim))
        
        scores.sort(key=lambda x: -x[1])
        
        resultados = []
        for idx, score in scores[:top_k]:
            if score > 0:
                resultados.append(ResultadoBusca(
                    documento=self.documentos[idx],
                    score_semantico=score,
                    score_combinado=score
                ))
        
        return resultados
    
    def _busca_hibrida(self, query: str, top_k: int) -> List[ResultadoBusca]:
        """Busca híbrida com Reciprocal Rank Fusion."""
        # Buscar com ambos os métodos
        bm25_results = self.bm25.search(query, top_k * 2)
        
        query_emb = self.embedder.encode(query)
        sem_scores = []
        for i, doc in enumerate(self.documentos):
            if doc.embedding is not None:
                sim = self.embedder.similarity(query_emb, doc.embedding)
                sem_scores.append((i, sim))
        sem_scores.sort(key=lambda x: -x[1])
        sem_results = sem_scores[:top_k * 2]
        
        # Reciprocal Rank Fusion
        rrf_scores: Dict[int, float] = {}
        bm25_score_map: Dict[int, float] = {}
        sem_score_map: Dict[int, float] = {}
        
        for rank, (idx, score) in enumerate(bm25_results):
            rrf_scores[idx] = rrf_scores.get(idx, 0) + (1 - self.alpha) / (self.rrf_k + rank + 1)
            bm25_score_map[idx] = score
        
        for rank, (idx, score) in enumerate(sem_results):
            rrf_scores[idx] = rrf_scores.get(idx, 0) + self.alpha / (self.rrf_k + rank + 1)
            sem_score_map[idx] = score
        
        # Ordenar por RRF score
        sorted_results = sorted(rrf_scores.items(), key=lambda x: -x[1])
        
        resultados = []
        for idx, rrf_score in sorted_results[:top_k]:
            resultados.append(ResultadoBusca(
                documento=self.documentos[idx],
                score_bm25=bm25_score_map.get(idx, 0),
                score_semantico=sem_score_map.get(idx, 0),
                score_combinado=rrf_score
            ))
        
        return resultados
    
    def estatisticas(self) -> dict:
        """Retorna estatísticas do índice."""
        return {
            "total_documentos": len(self.documentos),
            "vocabulario_bm25": len(self.bm25.doc_freq),
            "vocabulario_embedding": len(self.embedder.vocabulary),
            "dimensao_embedding": self.embedder.dim,
            "alpha": self.alpha,
            "indexado": self._indexado
        }


# Exemplo de uso
if __name__ == "__main__":
    # Documentos de exemplo
    docs = [
        {"id": "doc1", "conteudo": "A reforma agrária visa promover melhor distribuição da terra mediante modificações no regime de posse e uso.", "metadata": {"fonte": "Lei 4.504/64"}},
        {"id": "doc2", "conteudo": "O licenciamento ambiental é procedimento administrativo pelo qual o órgão ambiental competente licencia a localização e operação de empreendimentos.", "metadata": {"fonte": "Lei 6.938/81"}},
        {"id": "doc3", "conteudo": "A propriedade rural deve cumprir sua função social conforme critérios de produtividade, meio ambiente e bem-estar dos trabalhadores.", "metadata": {"fonte": "CF/88 Art. 186"}},
        {"id": "doc4", "conteudo": "O desmatamento ilegal em áreas de preservação permanente constitui crime ambiental sujeito a pena de reclusão.", "metadata": {"fonte": "Lei 9.605/98"}},
        {"id": "doc5", "conteudo": "A desapropriação por interesse social para fins de reforma agrária incide sobre o imóvel rural que não esteja cumprindo sua função social.", "metadata": {"fonte": "Lei 8.629/93"}},
    ]
    
    search = HybridSearch(alpha=0.5)
    n = search.indexar(docs)
    print(f"Documentos indexados: {n}")
    
    query = "reforma agrária e função social da propriedade rural"
    print(f"\nQuery: {query}")
    print("=" * 60)
    
    for r in search.buscar(query, top_k=3):
        print(f"\n[{r.documento.id}] Score: {r.score_combinado:.4f}")
        print(f"  BM25: {r.score_bm25:.4f} | Semântico: {r.score_semantico:.4f}")
        print(f"  {r.documento.conteudo[:100]}...")
