"""
EntityExtractor — Módulo de Extração de Entidades Jurídicas

Extrai entidades jurídicas de textos:
- Artigos de lei (Art. X)
- Parágrafos (§ Y)
- Leis e normas (Lei nº Z)
- Jurisprudências (STF, STJ, TST)
- Órgãos e tribunais
- Datas e prazos
- CPF/CNPJ (mascarados para LGPD)
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple
from enum import Enum


class TipoEntidade(Enum):
    """Tipos de entidades jurídicas reconhecidas."""
    ARTIGO = "artigo"
    PARAGRAFO = "paragrafo"
    INCISO = "inciso"
    ALINEA = "alinea"
    LEI = "lei"
    DECRETO = "decreto"
    MEDIDA_PROVISORIA = "medida_provisoria"
    CONSTITUICAO = "constituicao"
    SUMULA = "sumula"
    JURISPRUDENCIA = "jurisprudencia"
    TRIBUNAL = "tribunal"
    ORGAO = "orgao"
    DATA = "data"
    PRAZO = "prazo"
    VALOR_MONETARIO = "valor_monetario"
    CPF = "cpf"
    CNPJ = "cnpj"
    PROCESSO = "numero_processo"
    PESSOA = "pessoa"
    TEMA_JURIDICO = "tema_juridico"


@dataclass
class EntidadeJuridica:
    """Representa uma entidade jurídica extraída do texto."""
    tipo: TipoEntidade
    valor: str
    texto_original: str
    posicao_inicio: int
    posicao_fim: int
    confianca: float = 1.0
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "tipo": self.tipo.value,
            "valor": self.valor,
            "texto_original": self.texto_original,
            "posicao_inicio": self.posicao_inicio,
            "posicao_fim": self.posicao_fim,
            "confianca": self.confianca,
            "metadata": self.metadata
        }


class EntityExtractor:
    """
    Extrator de entidades jurídicas especializadas em legislação brasileira.
    
    Utiliza patterns regex otimizados para reconhecer:
    - Referências normativas (leis, decretos, artigos)
    - Jurisprudência (súmulas, acórdãos)
    - Órgãos e tribunais
    - Dados sensíveis (CPF/CNPJ — mascarados por LGPD)
    """
    
    # Padrões de reconhecimento
    PATTERNS: Dict[TipoEntidade, List[re.Pattern]] = {
        TipoEntidade.LEI: [
            re.compile(r'Lei\s+(?:n[°º]?\s*)?(\d[\d.]*(?:/\d{2,4})?)', re.IGNORECASE),
            re.compile(r'Lei\s+Complementar\s+(?:n[°º]?\s*)?(\d[\d.]*(?:/\d{2,4})?)', re.IGNORECASE),
            re.compile(r'Lei\s+Federal\s+(?:n[°º]?\s*)?(\d[\d.]*(?:/\d{2,4})?)', re.IGNORECASE),
            re.compile(r'Lei\s+Estadual\s+(?:n[°º]?\s*)?(\d[\d.]*(?:/\d{2,4})?)', re.IGNORECASE),
        ],
        TipoEntidade.DECRETO: [
            re.compile(r'Decreto(?:-[Ll]ei)?\s+(?:n[°º]?\s*)?(\d[\d.]*(?:/\d{2,4})?)', re.IGNORECASE),
        ],
        TipoEntidade.MEDIDA_PROVISORIA: [
            re.compile(r'Medida\s+Provisória\s+(?:n[°º]?\s*)?(\d[\d.]*(?:/\d{2,4})?)', re.IGNORECASE),
            re.compile(r'MP\s+(?:n[°º]?\s*)?(\d[\d.]*(?:/\d{2,4})?)', re.IGNORECASE),
        ],
        TipoEntidade.CONSTITUICAO: [
            re.compile(r'Constituição\s+Federal(?:\s+de\s+(\d{4}))?', re.IGNORECASE),
            re.compile(r'CF(?:/(\d{2,4}))?', re.IGNORECASE),
        ],
        TipoEntidade.ARTIGO: [
            re.compile(r'[Aa]rt(?:igo)?\.?\s*(\d+)[°º]?(?:\s*,?\s*(?:caput|§|inciso|alínea))?'),
        ],
        TipoEntidade.PARAGRAFO: [
            re.compile(r'§\s*(\d+)[°º]?'),
            re.compile(r'[Pp]arágrafo\s+único'),
        ],
        TipoEntidade.INCISO: [
            re.compile(r'[Ii]nciso\s+([IVXLCDM]+)'),
        ],
        TipoEntidade.ALINEA: [
            re.compile(r'[Aa]línea\s+["\']?([a-z])["\']?\)?\s'),
        ],
        TipoEntidade.SUMULA: [
            re.compile(r'Súmula\s+(?:Vinculante\s+)?(?:n[°º]?\s*)?(\d+)(?:\s+do\s+(STF|STJ|TST))?', re.IGNORECASE),
        ],
        TipoEntidade.JURISPRUDENCIA: [
            re.compile(r'(RE|REsp|HC|MS|ADI|ADPF|ADC)\s+(?:n[°º]?\s*)?(\d[\d./-]*)', re.IGNORECASE),
            re.compile(r'Acórdão\s+(?:n[°º]?\s*)?(\d[\d./-]*)', re.IGNORECASE),
        ],
        TipoEntidade.TRIBUNAL: [
            re.compile(r'\b(STF|STJ|TST|TSE|STM|TRF\d?|TJ[A-Z]{2}|TRT\d{1,2}|TRE[A-Z]{2}|CNJ)\b'),
        ],
        TipoEntidade.ORGAO: [
            re.compile(r'\b(IBAMA|MAPA|INCRA|FUNAI|ICMBio|ANVISA|CADE|TCU|CGU|MPF|MPT|MPE|DPU|AGU|OAB|CRM|CRO|CREA)\b'),
        ],
        TipoEntidade.DATA: [
            re.compile(r'(\d{1,2})\s+de\s+(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s+de\s+(\d{4})', re.IGNORECASE),
            re.compile(r'(\d{1,2}/\d{1,2}/\d{2,4})'),
        ],
        TipoEntidade.PRAZO: [
            re.compile(r'(\d+)\s+(dias?|meses?|anos?|horas?)(?:\s+(?:úteis|corridos|contados))?', re.IGNORECASE),
        ],
        TipoEntidade.VALOR_MONETARIO: [
            re.compile(r'R\$\s*(\d[\d.,]*)', re.IGNORECASE),
        ],
        TipoEntidade.CPF: [
            re.compile(r'(\d{3}[.\s]?\d{3}[.\s]?\d{3}[.\s-]?\d{2})'),
        ],
        TipoEntidade.CNPJ: [
            re.compile(r'(\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[.\s-]?\d{2})'),
        ],
        TipoEntidade.PROCESSO: [
            re.compile(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})'),
        ],
    }
    
    # Temas jurídicos comuns
    TEMAS_JURIDICOS: Dict[str, List[str]] = {
        "direito_agrario": [
            "reforma agrária", "propriedade rural", "função social da terra",
            "desapropriação", "assentamento", "estatuto da terra", "imóvel rural",
            "módulo rural", "produtividade", "colonização"
        ],
        "direito_ambiental": [
            "licenciamento ambiental", "área de preservação", "reserva legal",
            "desmatamento", "fauna", "flora", "poluição", "impacto ambiental",
            "crimes ambientais", "unidade de conservação"
        ],
        "direito_civil": [
            "contrato", "propriedade", "posse", "usucapião", "herança",
            "testamento", "responsabilidade civil", "dano moral", "obrigações"
        ],
        "direito_constitucional": [
            "direitos fundamentais", "habeas corpus", "mandado de segurança",
            "ação civil pública", "controle de constitucionalidade"
        ],
        "direito_trabalhista": [
            "CLT", "trabalho rural", "contrato de trabalho", "rescisão",
            "férias", "FGTS", "adicional", "insalubridade"
        ],
        "direito_penal": [
            "crime", "pena", "prisão", "dolo", "culpa", "legítima defesa",
            "prescrição", "inquérito", "ação penal"
        ],
    }
    
    def __init__(self, mascarar_dados_sensiveis: bool = True):
        """
        Args:
            mascarar_dados_sensiveis: Se True, mascara CPF/CNPJ por LGPD.
        """
        self.mascarar_dados_sensiveis = mascarar_dados_sensiveis
    
    def extrair(self, texto: str) -> List[EntidadeJuridica]:
        """
        Extrai todas as entidades jurídicas do texto.
        
        Args:
            texto: Texto jurídico para análise.
            
        Returns:
            Lista de entidades jurídicas encontradas, ordenadas por posição.
        """
        entidades: List[EntidadeJuridica] = []
        
        # Extrair entidades por padrões regex
        for tipo, patterns in self.PATTERNS.items():
            for pattern in patterns:
                for match in pattern.finditer(texto):
                    valor = match.group(1) if match.lastindex and match.lastindex >= 1 else match.group(0)
                    
                    # Mascarar dados sensíveis (LGPD)
                    if self.mascarar_dados_sensiveis and tipo in [TipoEntidade.CPF, TipoEntidade.CNPJ]:
                        valor = self._mascarar(valor, tipo)
                    
                    entidade = EntidadeJuridica(
                        tipo=tipo,
                        valor=valor,
                        texto_original=match.group(0),
                        posicao_inicio=match.start(),
                        posicao_fim=match.end(),
                        confianca=0.95
                    )
                    entidades.append(entidade)
        
        # Extrair temas jurídicos
        entidades.extend(self._extrair_temas(texto))
        
        # Remover duplicatas e ordenar por posição
        entidades = self._deduplicate(entidades)
        entidades.sort(key=lambda e: e.posicao_inicio)
        
        return entidades
    
    def _mascarar(self, valor: str, tipo: TipoEntidade) -> str:
        """Mascara dados sensíveis conforme LGPD."""
        digits = re.sub(r'\D', '', valor)
        if tipo == TipoEntidade.CPF and len(digits) == 11:
            return f"***.***.{digits[6:9]}-**"
        elif tipo == TipoEntidade.CNPJ and len(digits) == 14:
            return f"**.***.***/{digits[8:12]}-**"
        return "***MASCARADO***"
    
    def _extrair_temas(self, texto: str) -> List[EntidadeJuridica]:
        """Identifica temas jurídicos presentes no texto."""
        entidades = []
        texto_lower = texto.lower()
        
        temas_encontrados: Set[str] = set()
        
        for tema, termos in self.TEMAS_JURIDICOS.items():
            for termo in termos:
                pos = texto_lower.find(termo)
                if pos >= 0 and tema not in temas_encontrados:
                    temas_encontrados.add(tema)
                    entidade = EntidadeJuridica(
                        tipo=TipoEntidade.TEMA_JURIDICO,
                        valor=tema.replace("_", " ").title(),
                        texto_original=termo,
                        posicao_inicio=pos,
                        posicao_fim=pos + len(termo),
                        confianca=0.85,
                        metadata={"area": tema}
                    )
                    entidades.append(entidade)
                    break
        
        return entidades
    
    def _deduplicate(self, entidades: List[EntidadeJuridica]) -> List[EntidadeJuridica]:
        """Remove entidades duplicadas baseando-se em posição e tipo."""
        seen: Set[Tuple[int, int, str]] = set()
        resultado = []
        
        for ent in entidades:
            key = (ent.posicao_inicio, ent.posicao_fim, ent.tipo.value)
            if key not in seen:
                seen.add(key)
                resultado.append(ent)
        
        return resultado
    
    def extrair_referencias_cruzadas(self, texto: str) -> Dict[str, List[str]]:
        """
        Extrai e agrupa referências cruzadas entre normas.
        
        Returns:
            Dicionário com leis como chave e artigos referenciados como valores.
        """
        refs: Dict[str, List[str]] = {}
        
        # Padrão para "Art. X da Lei Y"
        pattern = re.compile(
            r'[Aa]rt\.?\s*(\d+)[°º]?\s+d[oae]\s+Lei\s+(?:n[°º]?\s*)?(\d[\d.]*(?:/\d{2,4})?)',
            re.IGNORECASE
        )
        
        for match in pattern.finditer(texto):
            artigo = f"Art. {match.group(1)}"
            lei = f"Lei {match.group(2)}"
            
            if lei not in refs:
                refs[lei] = []
            if artigo not in refs[lei]:
                refs[lei].append(artigo)
        
        return refs
    
    def resumo_entidades(self, entidades: List[EntidadeJuridica]) -> Dict[str, int]:
        """Retorna um resumo com contagem por tipo de entidade."""
        resumo: Dict[str, int] = {}
        for ent in entidades:
            tipo = ent.tipo.value
            resumo[tipo] = resumo.get(tipo, 0) + 1
        return dict(sorted(resumo.items(), key=lambda x: -x[1]))


# Exemplo de uso
if __name__ == "__main__":
    texto = """
    Conforme o Art. 1° da Lei 4.504/64 (Estatuto da Terra), a reforma agrária
    visa promover melhor distribuição da terra. O § 1° estabelece as diretrizes
    para a política agrícola. Ver também Súmula 456 do STJ e REsp 1.234.567/SP.
    
    O IBAMA e o MAPA são responsáveis pela fiscalização ambiental e agrícola,
    respectivamente. O prazo para manifestação é de 30 dias úteis.
    
    CPF do requerente: 123.456.789-00
    CNPJ da empresa: 12.345.678/0001-90
    Processo nº 0001234-56.2023.8.26.0100
    
    Valor da indenização: R$ 150.000,00
    Data do julgamento: 15 de março de 2024
    """
    
    extractor = EntityExtractor(mascarar_dados_sensiveis=True)
    entidades = extractor.extrair(texto)
    
    print("Entidades encontradas:")
    print("=" * 60)
    for ent in entidades:
        print(f"  [{ent.tipo.value}] {ent.valor} (confiança: {ent.confianca:.0%})")
    
    print(f"\nResumo: {extractor.resumo_entidades(entidades)}")
    print(f"\nReferências cruzadas: {extractor.extrair_referencias_cruzadas(texto)}")
