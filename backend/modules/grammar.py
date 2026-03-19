"""
GrammarCorrector — Módulo de Correção Gramatical Jurídica

Correção gramatical especializada em textos jurídicos brasileiros.
Verifica ortografia, concordância, e sugere melhorias de estilo
para linguagem jurídica formal.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum


class TipoCorrecao(Enum):
    """Tipos de correção gramatical."""
    ORTOGRAFIA = "ortografia"
    CONCORDANCIA = "concordancia"
    PONTUACAO = "pontuacao"
    ESTILO = "estilo"
    LATINISMO = "latinismo"
    ABREVIACAO = "abreviacao"
    REDUNDANCIA = "redundancia"
    FORMATACAO = "formatacao"


class Severidade(Enum):
    """Severidade da correção."""
    INFO = "info"
    AVISO = "aviso"
    ERRO = "erro"
    CRITICO = "critico"


@dataclass
class Correcao:
    """Representa uma correção sugerida."""
    tipo: TipoCorrecao
    severidade: Severidade
    texto_original: str
    sugestao: str
    explicacao: str
    posicao_inicio: int
    posicao_fim: int
    regra: str = ""
    
    def to_dict(self) -> dict:
        return {
            "tipo": self.tipo.value,
            "severidade": self.severidade.value,
            "texto_original": self.texto_original,
            "sugestao": self.sugestao,
            "explicacao": self.explicacao,
            "posicao_inicio": self.posicao_inicio,
            "posicao_fim": self.posicao_fim,
            "regra": self.regra
        }


class GrammarCorrector:
    """
    Corretor gramatical especializado em linguagem jurídica brasileira.
    
    Funcionalidades:
    - Correção ortográfica de termos jurídicos
    - Verificação de concordância nominal/verbal
    - Padronização de abreviações jurídicas
    - Sugestões de melhoria de estilo jurídico
    - Verificação de latinismos e expressões técnicas
    - Detecção de redundâncias comuns
    - Formatação de referências normativas
    """
    
    # Erros ortográficos comuns em textos jurídicos
    ORTOGRAFIA_JURIDICA: Dict[str, str] = {
        "mandado de seguranca": "mandado de segurança",
        "habeas-corpus": "habeas corpus",
        "habes corpus": "habeas corpus",
        "excecao": "exceção",
        "exceçao": "exceção",
        "peticao": "petição",
        "petiçao": "petição",
        "acordao": "acórdão",
        "acordão": "acórdão",
        "revel": "revel",
        "prescriçao": "prescrição",
        "prescricao": "prescrição",
        "constituiçao": "constituição",
        "constituicao": "constituição",
        "jurisdiçao": "jurisdição",
        "jurisdicao": "jurisdição",
        "usucapiao": "usucapião",
        "indenisação": "indenização",
        "indenisacao": "indenização",
        "restituiçao": "restituição",
        "apreençao": "apreensão",
        "apreensao": "apreensão",
        "desapropriaçao": "desapropriação",
        "desapropriacao": "desapropriação",
    }
    
    # Abreviações padronizadas
    ABREVIACOES: Dict[str, str] = {
        r'\bart\b\.?\s*(\d)': r'Art. \1',
        r'\barts\b\.?\s': 'Arts. ',
        r'\bpar\b\.?\s*(\d)': r'§ \1',
        r'\bparagrafo\s+unico\b': 'Parágrafo único',
        r'\binc\b\.?\s+([IVXLCDM]+)': r'Inciso \1',
        r'\bal\b\.?\s+([a-z])\)': r'Alínea \1)',
        r'\bn[°º]\b': 'nº',
        r'\bmin\b\.': 'Min.',
        r'\bdes\b\.': 'Des.',
        r'\bproc\b\.': 'Proc.',
        r'\bfl\b\.': 'fl.',
        r'\bfls\b\.': 'fls.',
        r'\bvol\b\.': 'vol.',
    }
    
    # Redundâncias comuns
    REDUNDANCIAS: List[Tuple[str, str, str]] = [
        ("elo de ligação", "elo", "A palavra 'elo' já significa ligação"),
        ("há anos atrás", "há anos", "'Há' já indica passado, dispensando 'atrás'"),
        ("a grande maioria", "a maioria", "'Maioria' já indica a maior parte"),
        ("todos foram unânimes", "foram unânimes", "'Unânimes' já significa todos"),
        ("juntada aos autos do processo", "juntada aos autos", "'Autos' já refere-se ao processo"),
        ("comparecer pessoalmente", "comparecer", "'Comparecer' já implica presença pessoal"),
        ("cada um dos réus", "cada réu", "Simplicação sem perda de sentido"),
        ("em face de tudo o que foi exposto", "ante o exposto", "Expressão jurídica mais concisa"),
        ("tendo em vista que", "considerando que", "Expressão jurídica mais adequada"),
    ]
    
    # Sugestões de estilo jurídico
    ESTILO_SUGESTOES: List[Tuple[str, str, str]] = [
        ("mesmo", "este/este último", "Evite usar 'mesmo' como pronome — use 'este' ou 'este último'"),
        ("onde", "em que/no qual", "Use 'onde' apenas para lugar físico — para referências normativas, use 'em que' ou 'no qual'"),
        ("através de", "por meio de/mediante", "Em linguagem jurídica formal, prefira 'por meio de' ou 'mediante'"),
        ("face ao exposto", "ante o exposto", "A forma mais aceita é 'ante o exposto'"),
        ("enquanto que", "enquanto/ao passo que", "'Enquanto que' é considerado inadequado — use 'enquanto' ou 'ao passo que'"),
        ("a nível de", "no âmbito de/em termos de", "'A nível de' é inadequado na linguagem formal"),
    ]
    
    # Latinismos com tradução
    LATINISMOS: Dict[str, str] = {
        "ad hoc": "para este fim",
        "ad referendum": "para referendo/aprovação",
        "data venia": "com a devida permissão",
        "de cujus": "falecido/autor da herança",
        "ex nunc": "a partir de agora (sem retroatividade)",
        "ex tunc": "desde então (com retroatividade)",
        "fumus boni iuris": "aparência do bom direito",
        "habeas corpus": "tenhas o corpo (garantia de liberdade)",
        "in dubio pro reo": "na dúvida, a favor do réu",
        "inter partes": "entre as partes",
        "jus postulandi": "direito de postular em juízo",
        "lato sensu": "em sentido amplo",
        "lex specialis": "lei especial",
        "mandamus": "mandamos (ordem judicial)",
        "periculum in mora": "perigo na demora",
        "stricto sensu": "em sentido estrito",
        "sub judice": "sob julgamento",
        "sui generis": "de espécie própria/único",
    }
    
    def __init__(self):
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pré-compila padrões regex para performance."""
        self._ortografia_patterns = {
            re.compile(re.escape(erro), re.IGNORECASE): correcao
            for erro, correcao in self.ORTOGRAFIA_JURIDICA.items()
        }
        
        self._redundancia_patterns = [
            (re.compile(re.escape(red), re.IGNORECASE), sug, expl)
            for red, sug, expl in self.REDUNDANCIAS
        ]
    
    def corrigir(self, texto: str) -> Tuple[str, List[Correcao]]:
        """
        Analisa e corrige texto jurídico.
        
        Args:
            texto: Texto jurídico para correção.
            
        Returns:
            Tupla (texto_corrigido, lista_de_correções).
        """
        correcoes: List[Correcao] = []
        texto_corrigido = texto
        
        # 1. Verificar ortografia jurídica
        correcoes.extend(self._verificar_ortografia(texto))
        
        # 2. Verificar abreviações
        correcoes.extend(self._verificar_abreviacoes(texto))
        
        # 3. Verificar redundâncias
        correcoes.extend(self._verificar_redundancias(texto))
        
        # 4. Verificar estilo
        correcoes.extend(self._verificar_estilo(texto))
        
        # 5. Verificar pontuação
        correcoes.extend(self._verificar_pontuacao(texto))
        
        # 6. Verificar formatação de referências
        correcoes.extend(self._verificar_formatacao(texto))
        
        # 7. Identificar latinismos (informativo)
        correcoes.extend(self._identificar_latinismos(texto))
        
        # Aplicar correções automáticas (apenas erros e críticos)
        for correcao in sorted(correcoes, key=lambda c: -c.posicao_inicio):
            if correcao.severidade in [Severidade.ERRO, Severidade.CRITICO]:
                texto_corrigido = (
                    texto_corrigido[:correcao.posicao_inicio] +
                    correcao.sugestao +
                    texto_corrigido[correcao.posicao_fim:]
                )
        
        # Ordenar correções por posição
        correcoes.sort(key=lambda c: c.posicao_inicio)
        
        return texto_corrigido, correcoes
    
    def _verificar_ortografia(self, texto: str) -> List[Correcao]:
        """Verifica erros ortográficos em termos jurídicos."""
        correcoes = []
        
        for pattern, correcao_str in self._ortografia_patterns.items():
            for match in pattern.finditer(texto):
                correcoes.append(Correcao(
                    tipo=TipoCorrecao.ORTOGRAFIA,
                    severidade=Severidade.ERRO,
                    texto_original=match.group(0),
                    sugestao=correcao_str,
                    explicacao=f"Grafia correta: '{correcao_str}'",
                    posicao_inicio=match.start(),
                    posicao_fim=match.end(),
                    regra="ORTOGRAFIA_JURIDICA"
                ))
        
        return correcoes
    
    def _verificar_abreviacoes(self, texto: str) -> List[Correcao]:
        """Verifica e padroniza abreviações jurídicas."""
        correcoes = []
        
        for pattern_str, replacement in self.ABREVIACOES.items():
            pattern = re.compile(pattern_str, re.IGNORECASE)
            for match in pattern.finditer(texto):
                sugestao = pattern.sub(replacement, match.group(0))
                if sugestao != match.group(0):
                    correcoes.append(Correcao(
                        tipo=TipoCorrecao.ABREVIACAO,
                        severidade=Severidade.AVISO,
                        texto_original=match.group(0),
                        sugestao=sugestao,
                        explicacao=f"Abreviação padronizada: '{sugestao}'",
                        posicao_inicio=match.start(),
                        posicao_fim=match.end(),
                        regra="ABREVIACAO_PADRAO"
                    ))
        
        return correcoes
    
    def _verificar_redundancias(self, texto: str) -> List[Correcao]:
        """Detecta redundâncias comuns em textos jurídicos."""
        correcoes = []
        
        for pattern, sugestao, explicacao in self._redundancia_patterns:
            for match in pattern.finditer(texto):
                correcoes.append(Correcao(
                    tipo=TipoCorrecao.REDUNDANCIA,
                    severidade=Severidade.AVISO,
                    texto_original=match.group(0),
                    sugestao=sugestao,
                    explicacao=explicacao,
                    posicao_inicio=match.start(),
                    posicao_fim=match.end(),
                    regra="REDUNDANCIA"
                ))
        
        return correcoes
    
    def _verificar_estilo(self, texto: str) -> List[Correcao]:
        """Sugere melhorias de estilo jurídico."""
        correcoes = []
        
        for termo, sugestao, explicacao in self.ESTILO_SUGESTOES:
            pattern = re.compile(r'\b' + re.escape(termo) + r'\b', re.IGNORECASE)
            for match in pattern.finditer(texto):
                correcoes.append(Correcao(
                    tipo=TipoCorrecao.ESTILO,
                    severidade=Severidade.INFO,
                    texto_original=match.group(0),
                    sugestao=sugestao,
                    explicacao=explicacao,
                    posicao_inicio=match.start(),
                    posicao_fim=match.end(),
                    regra="ESTILO_JURIDICO"
                ))
        
        return correcoes
    
    def _verificar_pontuacao(self, texto: str) -> List[Correcao]:
        """Verifica problemas de pontuação em textos jurídicos."""
        correcoes = []
        
        # Verificar espaço antes de pontuação
        pattern = re.compile(r'\s+([.,;:!?])')
        for match in pattern.finditer(texto):
            correcoes.append(Correcao(
                tipo=TipoCorrecao.PONTUACAO,
                severidade=Severidade.AVISO,
                texto_original=match.group(0),
                sugestao=match.group(1),
                explicacao="Remover espaço antes da pontuação",
                posicao_inicio=match.start(),
                posicao_fim=match.end(),
                regra="ESPACO_PONTUACAO"
            ))
        
        # Verificar dupla pontuação
        pattern = re.compile(r'([.,;:!?])\1+')
        for match in pattern.finditer(texto):
            correcoes.append(Correcao(
                tipo=TipoCorrecao.PONTUACAO,
                severidade=Severidade.ERRO,
                texto_original=match.group(0),
                sugestao=match.group(1),
                explicacao="Remover pontuação duplicada",
                posicao_inicio=match.start(),
                posicao_fim=match.end(),
                regra="DUPLICATA_PONTUACAO"
            ))
        
        return correcoes
    
    def _verificar_formatacao(self, texto: str) -> List[Correcao]:
        """Verifica formatação de referências normativas."""
        correcoes = []
        
        # Art. deve ser seguido de número com °
        pattern = re.compile(r'Art\.?\s*(\d+)\s')
        for match in pattern.finditer(texto):
            num = match.group(1)
            esperado = f"Art. {num}º " if int(num) <= 9 else f"Art. {num} "
            if match.group(0) != esperado:
                correcoes.append(Correcao(
                    tipo=TipoCorrecao.FORMATACAO,
                    severidade=Severidade.INFO,
                    texto_original=match.group(0),
                    sugestao=esperado,
                    explicacao=f"Formatação padrão: '{esperado.strip()}'",
                    posicao_inicio=match.start(),
                    posicao_fim=match.end(),
                    regra="FORMATO_ARTIGO"
                ))
        
        return correcoes
    
    def _identificar_latinismos(self, texto: str) -> List[Correcao]:
        """Identifica latinismos e fornece tradução."""
        correcoes = []
        
        for latinismo, traducao in self.LATINISMOS.items():
            pattern = re.compile(re.escape(latinismo), re.IGNORECASE)
            for match in pattern.finditer(texto):
                correcoes.append(Correcao(
                    tipo=TipoCorrecao.LATINISMO,
                    severidade=Severidade.INFO,
                    texto_original=match.group(0),
                    sugestao=match.group(0),  # Manter o latinismo
                    explicacao=f"Latinismo: '{latinismo}' = {traducao}",
                    posicao_inicio=match.start(),
                    posicao_fim=match.end(),
                    regra="LATINISMO"
                ))
        
        return correcoes
    
    def resumo_correcoes(self, correcoes: List[Correcao]) -> Dict[str, int]:
        """Gera resumo das correções por tipo e severidade."""
        por_tipo: Dict[str, int] = {}
        por_severidade: Dict[str, int] = {}
        
        for c in correcoes:
            por_tipo[c.tipo.value] = por_tipo.get(c.tipo.value, 0) + 1
            por_severidade[c.severidade.value] = por_severidade.get(c.severidade.value, 0) + 1
        
        return {"por_tipo": por_tipo, "por_severidade": por_severidade, "total": len(correcoes)}


# Exemplo de uso
if __name__ == "__main__":
    corrector = GrammarCorrector()
    
    texto = """
    Conforme o art 1 da Lei 4.504/64, o Estatuto da Terra estabelece através de 
    seus dispositivos a reforma agrária. O mandado de seguranca foi impetrado 
    face ao exposto, considerando o fumus boni iuris e o periculum in mora.
    
    A grande maioria dos réus compareceu pessoalmente à audiência ,, tendo em 
    vista que o habeas-corpus havia sido concedido há anos atrás.
    """
    
    texto_corrigido, correcoes = corrector.corrigir(texto)
    
    print("Correções encontradas:")
    print("=" * 60)
    for c in correcoes:
        icon = {"info": "ℹ️", "aviso": "⚠️", "erro": "❌", "critico": "🚨"}
        print(f"  {icon.get(c.severidade.value, '•')} [{c.tipo.value}] '{c.texto_original}' → '{c.sugestao}'")
        print(f"     {c.explicacao}")
    
    resumo = corrector.resumo_correcoes(correcoes)
    print(f"\nResumo: {resumo}")
