"""
Reranker — Módulo de Reranking Cross-Encoder PT-BR

Re-ordena os resultados de busca usando comparação par-a-par
query-documento para melhorar a precisão do ranking final.

Em produção, usar um modelo cross-encoder como:
- unicamp-dl/mMiniLM-L6-v2-pt-v2
- neuralmind/bert-base-portuguese-cased

Este módulo implementa um reranker baseado em features léxicas
e semânticas como demonstração funcional.
"""

import re
import math
from collections import Counter
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional


@dataclass
class ResultadoReranked:
    """Resultado após reranking com score detalhado."""
    id: str
    conteudo: str
    score_original: float
    score_reranked: float
    features: Dict[str, float]
    metadata: dict
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "conteudo": self.conteudo,
            "score_original": round(self.score_original, 4),
            "score_reranked": round(self.score_reranked, 4),
            "features": {k: round(v, 4) for k, v in self.features.items()},
            "metadata": self.metadata
        }


class Reranker:
    """
    Cross-Encoder Reranker para documentos jurídicos em PT-BR.
    
    Implementa reranking baseado em múltiplas features:
    1. Sobreposição de termos (term overlap)
    2. Cobertura da query
    3. Proximidade de termos
    4. Presença de termos jurídicos-chave
    5. Comprimento do documento (penalidade/bônus)
    6. Match exato de referências normativas
    """
    
    # Termos jurídicos com peso elevado (boost)
    TERMOS_JURIDICOS_PESO = {
        # Direito Agrário
        "reforma agrária": 2.0, "função social": 2.0, "propriedade rural": 1.8,
        "estatuto da terra": 1.8, "desapropriação": 1.5, "assentamento": 1.5,
        "imóvel rural": 1.5, "módulo rural": 1.5, "produtividade": 1.3,
        
        # Direito Ambiental
        "licenciamento ambiental": 2.0, "preservação permanente": 1.8,
        "reserva legal": 1.8, "desmatamento": 1.5, "crime ambiental": 1.5,
        
        # Termos processuais
        "jurisprudência": 1.5, "súmula": 1.8, "acórdão": 1.5,
        "sentença": 1.3, "decisão": 1.2, "recurso": 1.2,
        
        # Referências normativas
        "artigo": 1.2, "parágrafo": 1.2, "inciso": 1.2, "alínea": 1.2,
    }
    
    # Pesos das features no score final
    FEATURE_WEIGHTS = {
        "term_overlap": 0.25,
        "query_coverage": 0.20,
        "term_proximity": 0.15,
        "juridic_terms": 0.15,
        "exact_match": 0.10,
        "doc_quality": 0.10,
        "original_score": 0.05,
    }
    
    STOPWORDS = {
        "a", "o", "e", "de", "do", "da", "dos", "das", "em", "no", "na",
        "um", "uma", "por", "para", "com", "que", "se", "ao", "à", "ou",
        "como", "mais", "não", "seu", "sua", "foi", "são", "ser", "ter",
    }
    
    def __init__(self, top_k: int = 10):
        """
        Args:
            top_k: Número de documentos a retornar após reranking.
        """
        self.top_k = top_k
    
    def _tokenize(self, texto: str) -> List[str]:
        """Tokeniza e normaliza texto."""
        texto = texto.lower()
        texto = re.sub(r'[^\w\sáàâãéèêíìîóòôõúùûçü]', ' ', texto)
        tokens = texto.split()
        return [t for t in tokens if t not in self.STOPWORDS and len(t) > 1]
    
    def _bigrams(self, tokens: List[str]) -> List[str]:
        """Gera bigramas a partir de tokens."""
        return [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)]
    
    def rerank(
        self, 
        query: str, 
        resultados: List[Dict], 
        top_k: Optional[int] = None
    ) -> List[ResultadoReranked]:
        """
        Re-ordena resultados de busca com cross-encoding.
        
        Args:
            query: Consulta original.
            resultados: Lista de dicts com 'id', 'conteudo', 'score', 'metadata'.
            top_k: Número de resultados (padrão: self.top_k).
            
        Returns:
            Lista de ResultadoReranked ordenada por relevância.
        """
        k = top_k or self.top_k
        
        query_tokens = self._tokenize(query)
        query_bigrams = self._bigrams(query_tokens)
        query_set = set(query_tokens)
        
        reranked = []
        
        for resultado in resultados:
            conteudo = resultado.get("conteudo", "")
            doc_tokens = self._tokenize(conteudo)
            doc_set = set(doc_tokens)
            doc_bigrams = self._bigrams(doc_tokens)
            
            # Calcular features
            features = {}
            
            # 1. Term Overlap (Jaccard)
            intersection = query_set & doc_set
            union = query_set | doc_set
            features["term_overlap"] = len(intersection) / len(union) if union else 0
            
            # 2. Query Coverage
            features["query_coverage"] = len(intersection) / len(query_set) if query_set else 0
            
            # 3. Term Proximity (baseado em bigramas)
            bigram_overlap = set(query_bigrams) & set(doc_bigrams)
            features["term_proximity"] = (
                len(bigram_overlap) / len(query_bigrams) if query_bigrams else 0
            )
            
            # 4. Presença de termos jurídicos com peso
            juridic_score = 0.0
            texto_lower = conteudo.lower()
            for termo, peso in self.TERMOS_JURIDICOS_PESO.items():
                if termo in texto_lower and termo in query.lower():
                    juridic_score += peso
            max_possible = sum(
                peso for termo, peso in self.TERMOS_JURIDICOS_PESO.items() 
                if termo in query.lower()
            )
            features["juridic_terms"] = (
                juridic_score / max_possible if max_possible > 0 else 0
            )
            
            # 5. Match exato de referências normativas
            ref_pattern = re.compile(r'(?:Art\.\s*\d+|Lei\s+[\d./]+|§\s*\d+|Súmula\s+\d+)', re.IGNORECASE)
            query_refs = set(ref_pattern.findall(query.lower()))
            doc_refs = set(ref_pattern.findall(texto_lower))
            ref_match = len(query_refs & doc_refs) / len(query_refs) if query_refs else 0.5
            features["exact_match"] = ref_match
            
            # 6. Qualidade do documento
            doc_len = len(doc_tokens)
            ideal_len = 100  # comprimento ideal em tokens
            features["doc_quality"] = min(1.0, 1.0 - abs(doc_len - ideal_len) / (ideal_len * 3))
            features["doc_quality"] = max(0.0, features["doc_quality"])
            
            # 7. Score original (normalizado)
            original_score = resultado.get("score", 0)
            features["original_score"] = min(1.0, original_score)
            
            # Score final ponderado
            score_reranked = sum(
                features.get(feat, 0) * weight 
                for feat, weight in self.FEATURE_WEIGHTS.items()
            )
            
            reranked.append(ResultadoReranked(
                id=resultado.get("id", ""),
                conteudo=conteudo,
                score_original=original_score,
                score_reranked=score_reranked,
                features=features,
                metadata=resultado.get("metadata", {})
            ))
        
        # Ordenar por score
        reranked.sort(key=lambda x: -x.score_reranked)
        
        return reranked[:k]
    
    def explain(self, resultado: ResultadoReranked) -> str:
        """Gera uma explicação legível do score de reranking."""
        lines = [
            f"Documento: {resultado.id}",
            f"Score Original: {resultado.score_original:.4f}",
            f"Score Reranked: {resultado.score_reranked:.4f}",
            f"",
            f"Detalhamento das Features:"
        ]
        
        for feat, weight in sorted(
            self.FEATURE_WEIGHTS.items(), 
            key=lambda x: -x[1]
        ):
            valor = resultado.features.get(feat, 0)
            contribuicao = valor * weight
            bar = "█" * int(valor * 20)
            lines.append(
                f"  {feat:20s} = {valor:.3f} × {weight:.2f} = {contribuicao:.4f} |{bar}"
            )
        
        return "\n".join(lines)


# Exemplo de uso
if __name__ == "__main__":
    reranker = Reranker(top_k=3)
    
    query = "reforma agrária e função social da propriedade rural"
    
    resultados = [
        {
            "id": "doc1",
            "conteudo": "A reforma agrária visa promover melhor distribuição da terra mediante modificações no regime de posse e uso da propriedade rural.",
            "score": 0.85,
            "metadata": {"fonte": "Lei 4.504/64"}
        },
        {
            "id": "doc2",
            "conteudo":"O licenciamento ambiental é procedimento administrativo pelo qual o órgão competente licencia empreendimentos.",
            "score": 0.65,
            "metadata": {"fonte": "Lei 6.938/81"}
        },
        {
            "id": "doc3",
            "conteudo": "A propriedade rural deve cumprir sua função social conforme critérios estabelecidos na Constituição Federal.",
            "score": 0.75,
            "metadata": {"fonte": "CF/88"}
        },
    ]
    
    reranked = reranker.rerank(query, resultados)
    
    for r in reranked:
        print(f"\n{'='*60}")
        print(reranker.explain(r))
