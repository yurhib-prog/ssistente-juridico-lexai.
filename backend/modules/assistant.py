"""
JuridicAssistant — Classe Principal do Assistente Jurídico

Integra todos os módulos do sistema:
- ChunkingJuridico: segmentação de documentos
- EntityExtractor: extração de entidades
- HybridSearch: busca híbrida
- Reranker: reranking de resultados
- GrammarCorrector: correção gramatical

Retorna: resposta + score de confiança + temas + entidades
"""

import json
import time
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from .chunking import ChunkingJuridico, ChunkJuridico
from .entities import EntityExtractor, EntidadeJuridica
from .search import HybridSearch, ResultadoBusca
from .reranking import Reranker, ResultadoReranked
from .grammar import GrammarCorrector, Correcao


@dataclass
class RespostaAssistente:
    """Resposta completa do assistente jurídico."""
    query_original: str
    query_corrigida: str
    resposta: str
    score_confianca: float
    temas: List[str]
    entidades: List[Dict]
    documentos_relevantes: List[Dict]
    correcoes_gramaticais: List[Dict]
    referencias_normativas: Dict[str, List[str]]
    tempo_processamento: float
    timestamp: str
    session_id: str = ""
    
    def to_dict(self) -> dict:
        return {
            "query_original": self.query_original,
            "query_corrigida": self.query_corrigida,
            "resposta": self.resposta,
            "score_confianca": round(self.score_confianca, 4),
            "temas": self.temas,
            "entidades": self.entidades,
            "documentos_relevantes": self.documentos_relevantes,
            "correcoes_gramaticais": self.correcoes_gramaticais,
            "referencias_normativas": self.referencias_normativas,
            "tempo_processamento": round(self.tempo_processamento, 3),
            "timestamp": self.timestamp,
            "session_id": self.session_id
        }
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class JuridicAssistant:
    """
    Assistente Jurídico com IA — Classe Principal.
    
    Orquestra todos os módulos do sistema para:
    1. Receber e preprocessar queries jurídicas
    2. Corrigir gramática e padronizar termos
    3. Buscar documentos relevantes (BM25 + semântico)
    4. Re-ranquear resultados por relevância
    5. Extrair entidades e referências normativas
    6. Gerar resposta com score de confiança
    
    Integra as seguintes camadas da arquitetura:
    - Interface → Preprocessamento → Pipeline RAG → Geração → Saída
    """
    
    # Base de conhecimento jurídico pré-definida
    BASE_CONHECIMENTO = [
        {
            "id": "lei_4504_art1",
            "conteudo": "Art. 1º Esta Lei regula os direitos e obrigações concernentes aos bens imóveis rurais, para os fins de execução da Reforma Agrária e promoção da Política Agrícola. § 1º Considera-se Reforma Agrária o conjunto de medidas que visem a promover melhor distribuição da terra, mediante modificações no regime de sua posse e uso, a fim de atender aos princípios de justiça social e ao aumento de produtividade.",
            "metadata": {"fonte": "Lei 4.504/64 - Estatuto da Terra", "tipo": "legislação", "area": "direito_agrario"}
        },
        {
            "id": "lei_4504_art2",
            "conteudo": "Art. 2º É assegurada a todos a oportunidade de acesso à propriedade da terra, condicionada pela sua função social, na forma prevista nesta Lei. § 1º A propriedade da terra desempenha integralmente a sua função social quando, simultaneamente: a) favorece o bem-estar dos proprietários e dos trabalhadores que nela labutam, assim como de suas famílias; b) mantém níveis satisfatórios de produtividade; c) assegura a conservação dos recursos naturais; d) observa as disposições legais que regulam as justas relações de trabalho entre os que a possuem e a cultivem.",
            "metadata": {"fonte": "Lei 4.504/64 - Estatuto da Terra", "tipo": "legislação", "area": "direito_agrario"}
        },
        {
            "id": "cf88_art184",
            "conteudo": "Art. 184. Compete à União desapropriar por interesse social, para fins de reforma agrária, o imóvel rural que não esteja cumprindo sua função social, mediante prévia e justa indenização em títulos da dívida agrária, com cláusula de preservação do valor real, resgatáveis no prazo de até vinte anos, a partir do segundo ano de sua emissão, e cuja utilização será definida em lei.",
            "metadata": {"fonte": "Constituição Federal de 1988", "tipo": "constituição", "area": "direito_agrario"}
        },
        {
            "id": "cf88_art186",
            "conteudo": "Art. 186. A função social é cumprida quando a propriedade rural atende, simultaneamente, segundo critérios e graus de exigência estabelecidos em lei, aos seguintes requisitos: I - aproveitamento racional e adequado; II - utilização adequada dos recursos naturais disponíveis e preservação do meio ambiente; III - observância das disposições que regulam as relações de trabalho; IV - exploração que favoreça o bem-estar dos proprietários e dos trabalhadores.",
            "metadata": {"fonte": "Constituição Federal de 1988", "tipo": "constituição", "area": "direito_agrario"}
        },
        {
            "id": "lei_8629_art6",
            "conteudo": "Art. 6º Considera-se propriedade produtiva aquela que, explorada econômica e racionalmente, atinge, simultaneamente, graus de utilização da terra e de eficiência na exploração, segundo índices fixados pelo órgão federal competente. § 1º O grau de utilização da terra, para efeito do caput deste artigo, deverá ser igual ou superior a 80%, calculado pela relação percentual entre a área efetivamente utilizada e a área aproveitável total do imóvel.",
            "metadata": {"fonte": "Lei 8.629/93", "tipo": "legislação", "area": "direito_agrario"}
        },
        {
            "id": "lei_6938_art2",
            "conteudo": "Art. 2º A Política Nacional do Meio Ambiente tem por objetivo a preservação, melhoria e recuperação da qualidade ambiental propícia à vida, visando assegurar, no País, condições ao desenvolvimento socioeconômico, aos interesses da segurança nacional e à proteção da dignidade da vida humana.",
            "metadata": {"fonte": "Lei 6.938/81 - Política Nacional do Meio Ambiente", "tipo": "legislação", "area": "direito_ambiental"}
        },
        {
            "id": "lei_9605_art38",
            "conteudo": "Art. 38. Destruir ou danificar floresta considerada de preservação permanente, mesmo que em formação, ou utilizá-la com infringência das normas de proteção: Pena - detenção, de um a três anos, ou multa, ou ambas as penas cumulativamente. Parágrafo único. Se o crime for culposo, a pena será reduzida à metade.",
            "metadata": {"fonte": "Lei 9.605/98 - Crimes Ambientais", "tipo": "legislação", "area": "direito_ambiental"}
        },
        {
            "id": "lei_12651_art3",
            "conteudo": "Art. 3º Para os efeitos desta Lei, entende-se por: II - Área de Preservação Permanente (APP): área protegida, coberta ou não por vegetação nativa, com a função ambiental de preservar os recursos hídricos, a paisagem, a estabilidade geológica e a biodiversidade, facilitar o fluxo gênico de fauna e flora, proteger o solo e assegurar o bem-estar das populações humanas.",
            "metadata": {"fonte": "Lei 12.651/12 - Código Florestal", "tipo": "legislação", "area": "direito_ambiental"}
        },
        {
            "id": "sumula_stj_456",
            "conteudo": "Súmula 456 do STJ: É legítima a cobrança de tarifa básica pelo uso dos serviços de telefonia fixa. O tribunal reconhece a constitucionalidade da cobrança mediante fundamentação em legislação infraconstitucional vigente.",
            "metadata": {"fonte": "STJ - Súmula 456", "tipo": "jurisprudência", "area": "direito_civil"}
        },
        {
            "id": "stf_adi_3239",
            "conteudo": "ADI 3239 - Terras Quilombolas: O STF decidiu que o marco temporal para reconhecimento de terras quilombolas não deve se limitar à data da promulgação da CF/88, reconhecendo o direito de propriedade das comunidades quilombolas de forma ampla, com base no Art. 68 do ADCT.",
            "metadata": {"fonte": "STF - ADI 3239", "tipo": "jurisprudência", "area": "direito_agrario"}
        },
    ]
    
    def __init__(
        self,
        max_chunk_size: int = 512,
        search_alpha: float = 0.5,
        top_k: int = 5,
        mascarar_lgpd: bool = True
    ):
        """
        Inicializa o assistente jurídico com configurações.
        
        Args:
            max_chunk_size: Tamanho máximo de chunks.
            search_alpha: Peso semântico na busca híbrida.
            top_k: Número de documentos a retornar.
            mascarar_lgpd: Mascarar dados sensíveis (CPF/CNPJ).
        """
        # Inicializar módulos
        self.chunker = ChunkingJuridico(max_chunk_size=max_chunk_size)
        self.entity_extractor = EntityExtractor(mascarar_dados_sensiveis=mascarar_lgpd)
        self.search = HybridSearch(alpha=search_alpha)
        self.reranker = Reranker(top_k=top_k)
        self.grammar = GrammarCorrector()
        
        self.top_k = top_k
        self._session_id = hashlib.md5(
            str(datetime.now().timestamp()).encode()
        ).hexdigest()[:12]
        
        # Indexar base de conhecimento
        self._indexar_base()
        
        # Histórico de consultas
        self.historico: List[RespostaAssistente] = []
    
    def _indexar_base(self) -> None:
        """Indexa a base de conhecimento jurídico."""
        self.search.indexar(self.BASE_CONHECIMENTO)
    
    def adicionar_documentos(self, documentos: List[Dict[str, str]]) -> int:
        """
        Adiciona documentos à base de conhecimento.
        
        Args:
            documentos: Lista de dicts com 'id', 'conteudo', e 'metadata'.
            
        Returns:
            Número total de documentos na base.
        """
        all_docs = self.BASE_CONHECIMENTO + documentos
        return self.search.indexar(all_docs)
    
    def adicionar_documento_texto(self, texto: str, fonte: str = "") -> int:
        """
        Adiciona um documento em texto plano, realizando chunking automático.
        
        Args:
            texto: Texto completo do documento.
            fonte: Identificação da fonte.
            
        Returns:
            Número de chunks gerados.
        """
        chunks = self.chunker.chunking_estrutural(texto, fonte=fonte)
        
        docs = [
            {
                "id": chunk.id,
                "conteudo": chunk.conteudo,
                "metadata": {
                    "fonte": fonte,
                    "tipo": chunk.tipo.value,
                    "hierarquia": chunk.hierarquia
                }
            }
            for chunk in chunks
        ]
        
        if docs:
            all_docs = self.BASE_CONHECIMENTO + docs
            self.search.indexar(all_docs)
        
        return len(docs)
    
    def consultar(self, query: str) -> RespostaAssistente:
        """
        Processa uma consulta jurídica completa.
        
        Pipeline:
        1. Correção gramatical da query
        2. Extração de entidades da query
        3. Busca híbrida de documentos relevantes
        4. Reranking dos resultados
        5. Extração de entidades dos resultados
        6. Geração de resposta com confiança
        
        Args:
            query: Pergunta ou consulta jurídica.
            
        Returns:
            RespostaAssistente completa.
        """
        inicio = time.time()
        
        # 1. Correção gramatical
        query_corrigida, correcoes_query = self.grammar.corrigir(query)
        
        # 2. Extração de entidades da query
        entidades_query = self.entity_extractor.extrair(query_corrigida)
        
        # 3. Busca híbrida
        resultados_busca = self.search.buscar(query_corrigida, top_k=self.top_k * 2)
        
        # 4. Reranking
        resultados_dict = [
            {
                "id": r.documento.id,
                "conteudo": r.documento.conteudo,
                "score": r.score_combinado,
                "metadata": r.documento.metadata
            }
            for r in resultados_busca
        ]
        
        resultados_reranked = self.reranker.rerank(
            query_corrigida, resultados_dict, top_k=self.top_k
        )
        
        # 5. Extrair entidades dos documentos relevantes
        todas_entidades = list(entidades_query)
        for resultado in resultados_reranked:
            entidades_doc = self.entity_extractor.extrair(resultado.conteudo)
            todas_entidades.extend(entidades_doc)
        
        # 6. Identificar temas
        temas = list(set(
            ent.valor for ent in todas_entidades 
            if ent.tipo.value == "tema_juridico"
        ))
        
        # 7. Referências cruzadas
        todos_textos = query_corrigida + " " + " ".join(
            r.conteudo for r in resultados_reranked
        )
        referencias = self.entity_extractor.extrair_referencias_cruzadas(todos_textos)
        
        # 8. Gerar resposta
        resposta, confianca = self._gerar_resposta(
            query_corrigida, resultados_reranked, todas_entidades
        )
        
        # 9. Correção gramatical da resposta
        resposta_corrigida, correcoes_resposta = self.grammar.corrigir(resposta)
        
        tempo = time.time() - inicio
        
        resultado_final = RespostaAssistente(
            query_original=query,
            query_corrigida=query_corrigida,
            resposta=resposta_corrigida,
            score_confianca=confianca,
            temas=temas,
            entidades=[ent.to_dict() for ent in todas_entidades[:20]],
            documentos_relevantes=[r.to_dict() for r in resultados_reranked],
            correcoes_gramaticais=[c.to_dict() for c in correcoes_query],
            referencias_normativas=referencias,
            tempo_processamento=tempo,
            timestamp=datetime.now().isoformat(),
            session_id=self._session_id
        )
        
        # Salvar no histórico
        self.historico.append(resultado_final)
        
        return resultado_final
    
    def _gerar_resposta(
        self, 
        query: str, 
        resultados: List[ResultadoReranked],
        entidades: List[EntidadeJuridica]
    ) -> Tuple[str, float]:
        """
        Gera resposta baseada nos documentos recuperados.
        
        Em produção, esta função chamaria o LLM (Sabiá-3 / GPT-4o).
        Na demonstração, gera uma resposta estruturada a partir dos documentos.
        
        Returns:
            Tupla (resposta_texto, score_confiança).
        """
        if not resultados:
            return (
                "Não foram encontrados documentos relevantes para sua consulta. "
                "Tente reformular a pergunta com termos jurídicos mais específicos.",
                0.0
            )
        
        # Calcular confiança baseada nos scores
        scores = [r.score_reranked for r in resultados]
        confianca = min(1.0, sum(scores) / len(scores) * 5)
        
        # Construir resposta estruturada
        partes = []
        
        # Introdução
        partes.append(f"📋 **Análise Jurídica**\n")
        partes.append(f"Com base na análise dos documentos recuperados, apresentamos "
                      f"os seguintes resultados para sua consulta:\n")
        
        # Documentos relevantes
        partes.append(f"\n📚 **Fundamentos Legais Encontrados:**\n")
        
        for i, r in enumerate(resultados[:3], 1):
            fonte = r.metadata.get("fonte", "Fonte não identificada")
            partes.append(f"\n**{i}. {fonte}** (relevância: {r.score_reranked:.0%})")
            
            # Resumo do conteúdo
            conteudo = r.conteudo
            if len(conteudo) > 300:
                conteudo = conteudo[:300] + "..."
            partes.append(f"\n> {conteudo}\n")
        
        # Entidades identificadas
        tipos_importantes = {"lei", "artigo", "sumula", "jurisprudencia", "tribunal"}
        entidades_relevantes = [
            e for e in entidades 
            if e.tipo.value in tipos_importantes
        ]
        
        if entidades_relevantes:
            partes.append(f"\n🏛️ **Referências Normativas Identificadas:**\n")
            refs_unicas = set()
            for ent in entidades_relevantes:
                ref = f"- {ent.tipo.value.replace('_', ' ').title()}: {ent.valor}"
                if ref not in refs_unicas:
                    refs_unicas.add(ref)
                    partes.append(ref)
        
        # Temas
        temas = list(set(
            e.valor for e in entidades if e.tipo.value == "tema_juridico"
        ))
        if temas:
            partes.append(f"\n📎 **Temas Jurídicos:** {', '.join(temas)}")
        
        # Nota de confiança
        nivel = "alta" if confianca > 0.7 else "média" if confianca > 0.4 else "baixa"
        partes.append(f"\n\n⚖️ **Confiança da análise:** {confianca:.0%} ({nivel})")
        partes.append(f"\n\n⚠️ *Esta análise é gerada automaticamente e não substitui "
                      f"a consulta a um profissional jurídico qualificado.*")
        
        resposta = "\n".join(partes)
        return resposta, confianca
    
    def analisar_documento(self, texto: str, fonte: str = "") -> Dict:
        """
        Analisa um documento jurídico completo.
        
        Retorna estrutura, entidades, correções e sugestões.
        """
        # Chunking
        chunks = self.chunker.chunking_estrutural(texto, fonte=fonte)
        
        # Entidades
        entidades = self.entity_extractor.extrair(texto)
        
        # Correção gramatical
        texto_corrigido, correcoes = self.grammar.corrigir(texto)
        
        # Referências cruzadas
        referencias = self.entity_extractor.extrair_referencias_cruzadas(texto)
        
        # Resumo
        resumo_entidades = self.entity_extractor.resumo_entidades(entidades)
        resumo_correcoes = self.grammar.resumo_correcoes(correcoes)
        
        return {
            "fonte": fonte,
            "num_chunks": len(chunks),
            "chunks": [c.to_dict() for c in chunks],
            "entidades": [e.to_dict() for e in entidades],
            "resumo_entidades": resumo_entidades,
            "correcoes": [c.to_dict() for c in correcoes],
            "resumo_correcoes": resumo_correcoes,
            "texto_corrigido": texto_corrigido,
            "referencias_cruzadas": referencias,
            "timestamp": datetime.now().isoformat()
        }
    
    def estatisticas(self) -> Dict:
        """Retorna estatísticas do sistema."""
        return {
            "total_consultas": len(self.historico),
            "session_id": self._session_id,
            "indice": self.search.estatisticas(),
            "base_conhecimento": len(self.BASE_CONHECIMENTO),
            "ultimo_query": self.historico[-1].query_original if self.historico else None,
        }


# Exemplo de uso
if __name__ == "__main__":
    print("🏛️ Iniciando Assistente Jurídico...")
    print("=" * 60)
    
    assistant = JuridicAssistant(top_k=3)
    
    # Consulta 1
    query = "Qual a função social da propriedade rural na reforma agrária?"
    print(f"\n📝 Consulta: {query}")
    print("-" * 60)
    
    resposta = assistant.consultar(query)
    print(resposta.resposta)
    print(f"\n⏱️ Tempo: {resposta.tempo_processamento:.3f}s")
    
    # Consulta 2
    print("\n" + "=" * 60)
    query2 = "Desmatamento em area de preservação permanente é crime?"
    print(f"\n📝 Consulta: {query2}")
    print("-" * 60)
    
    resposta2 = assistant.consultar(query2)
    print(resposta2.resposta)
    
    # Estatísticas
    print("\n" + "=" * 60)
    print(f"\n📊 Estatísticas: {json.dumps(assistant.estatisticas(), ensure_ascii=False, indent=2)}")
