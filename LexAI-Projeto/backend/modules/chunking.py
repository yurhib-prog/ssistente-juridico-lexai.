"""
ChunkingJuridico — Módulo de Segmentação de Documentos Jurídicos

Divide documentos jurídicos respeitando a estrutura hierárquica:
- Artigos (Art.)
- Parágrafos (§)
- Incisos (I, II, III...)
- Alíneas (a), b), c)...)

Preserva o contexto hierárquico da norma para indexação eficiente.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class TipoElemento(Enum):
    """Tipos de elementos da estrutura jurídica."""
    TITULO = "titulo"
    CAPITULO = "capitulo"
    SECAO = "secao"
    ARTIGO = "artigo"
    PARAGRAFO = "paragrafo"
    INCISO = "inciso"
    ALINEA = "alinea"
    CAPUT = "caput"
    EMENTA = "ementa"
    PREAMBULO = "preambulo"
    TEXTO_LIVRE = "texto_livre"


@dataclass
class ChunkJuridico:
    """Representa um fragmento de documento jurídico com contexto hierárquico."""
    id: str
    tipo: TipoElemento
    conteudo: str
    hierarquia: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    posicao_inicio: int = 0
    posicao_fim: int = 0
    
    def contexto_completo(self) -> str:
        """Retorna o contexto hierárquico completo como string."""
        return " > ".join(self.hierarquia + [self.conteudo[:80]])
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tipo": self.tipo.value,
            "conteudo": self.conteudo,
            "hierarquia": self.hierarquia,
            "metadata": self.metadata,
            "contexto_completo": self.contexto_completo()
        }


class ChunkingJuridico:
    """
    Módulo de chunking especializado em documentos jurídicos brasileiros.
    
    Respeita a estrutura normativa: Títulos > Capítulos > Seções > 
    Artigos > Parágrafos > Incisos > Alíneas.
    """
    
    # Padrões regex para identificação de elementos jurídicos
    PATTERNS = {
        TipoElemento.TITULO: re.compile(
            r'^(?:TÍTULO|Título)\s+([IVXLCDM]+|[0-9]+)\s*[-–—.]?\s*(.*)', re.MULTILINE
        ),
        TipoElemento.CAPITULO: re.compile(
            r'^(?:CAPÍTULO|Capítulo)\s+([IVXLCDM]+|[0-9]+)\s*[-–—.]?\s*(.*)', re.MULTILINE
        ),
        TipoElemento.SECAO: re.compile(
            r'^(?:SEÇÃO|Seção|SUBSEÇÃO|Subseção)\s+([IVXLCDM]+|[0-9]+)\s*[-–—.]?\s*(.*)', re.MULTILINE
        ),
        TipoElemento.ARTIGO: re.compile(
            r'^(?:Art\.|Artigo)\s*(\d+)[°º]?\s*[-–—.]?\s*(.*)', re.MULTILINE
        ),
        TipoElemento.PARAGRAFO: re.compile(
            r'^(?:§\s*(\d+)[°º]?|Parágrafo\s+único)\s*[-–—.]?\s*(.*)', re.MULTILINE
        ),
        TipoElemento.INCISO: re.compile(
            r'^\s*([IVXLCDM]+)\s*[-–—]\s*(.*)', re.MULTILINE
        ),
        TipoElemento.ALINEA: re.compile(
            r'^\s*([a-z])\)\s*(.*)', re.MULTILINE
        ),
    }
    
    def __init__(self, max_chunk_size: int = 512, overlap: int = 50):
        """
        Args:
            max_chunk_size: Tamanho máximo de cada chunk em caracteres.
            overlap: Sobreposição entre chunks adjacentes.
        """
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self._chunk_counter = 0
    
    def _gerar_id(self) -> str:
        """Gera um ID único para cada chunk."""
        self._chunk_counter += 1
        return f"chunk_{self._chunk_counter:06d}"
    
    def _identificar_tipo(self, linha: str) -> Optional[TipoElemento]:
        """Identifica o tipo de elemento jurídico de uma linha."""
        for tipo, pattern in self.PATTERNS.items():
            if pattern.match(linha.strip()):
                return tipo
        return None
    
    def _extrair_referencia(self, linha: str, tipo: TipoElemento) -> str:
        """Extrai a referência (número/letra) do elemento."""
        pattern = self.PATTERNS.get(tipo)
        if pattern:
            match = pattern.match(linha.strip())
            if match:
                return match.group(1) if match.group(1) else "único"
        return ""
    
    def chunking_estrutural(self, texto: str, fonte: str = "") -> List[ChunkJuridico]:
        """
        Realiza o chunking respeitando a estrutura jurídica do documento.
        
        Args:
            texto: Texto completo do documento jurídico.
            fonte: Identificação da fonte (ex: "Lei 4.504/64").
            
        Returns:
            Lista de ChunkJuridico com contexto hierárquico preservado.
        """
        self._chunk_counter = 0
        chunks = []
        linhas = texto.split('\n')
        
        # Estado da hierarquia atual
        hierarquia = {
            TipoElemento.TITULO: "",
            TipoElemento.CAPITULO: "",
            TipoElemento.SECAO: "",
            TipoElemento.ARTIGO: "",
        }
        
        buffer_atual = []
        tipo_atual = TipoElemento.TEXTO_LIVRE
        posicao = 0
        
        for i, linha in enumerate(linhas):
            tipo_identificado = self._identificar_tipo(linha)
            
            if tipo_identificado and tipo_identificado in [
                TipoElemento.TITULO, TipoElemento.CAPITULO, 
                TipoElemento.SECAO, TipoElemento.ARTIGO
            ]:
                # Salvar o buffer atual como chunk
                if buffer_atual:
                    conteudo = '\n'.join(buffer_atual).strip()
                    if conteudo:
                        chunks.extend(
                            self._criar_chunks(conteudo, tipo_atual, hierarquia, fonte, posicao)
                        )
                
                # Atualizar hierarquia
                ref = self._extrair_referencia(linha, tipo_identificado)
                label = f"{tipo_identificado.value.capitalize()} {ref}"
                hierarquia[tipo_identificado] = label
                
                # Limpar níveis inferiores
                niveis = list(hierarquia.keys())
                idx = niveis.index(tipo_identificado)
                for nivel in niveis[idx + 1:]:
                    hierarquia[nivel] = ""
                
                # Reiniciar buffer
                buffer_atual = [linha]
                tipo_atual = tipo_identificado
                posicao = i
                
            elif tipo_identificado in [TipoElemento.PARAGRAFO, TipoElemento.INCISO, TipoElemento.ALINEA]:
                buffer_atual.append(linha)
            else:
                buffer_atual.append(linha)
        
        # Processar último buffer
        if buffer_atual:
            conteudo = '\n'.join(buffer_atual).strip()
            if conteudo:
                chunks.extend(
                    self._criar_chunks(conteudo, tipo_atual, hierarquia, fonte, posicao)
                )
        
        return chunks
    
    def _criar_chunks(
        self, 
        conteudo: str, 
        tipo: TipoElemento, 
        hierarquia: dict, 
        fonte: str,
        posicao: int
    ) -> List[ChunkJuridico]:
        """Cria chunks respeitando o tamanho máximo com overlap."""
        chunks = []
        
        # Construir hierarquia como lista
        hier_lista = [fonte] if fonte else []
        for _, valor in hierarquia.items():
            if valor:
                hier_lista.append(valor)
        
        if len(conteudo) <= self.max_chunk_size:
            chunk = ChunkJuridico(
                id=self._gerar_id(),
                tipo=tipo,
                conteudo=conteudo,
                hierarquia=hier_lista.copy(),
                metadata={"fonte": fonte, "tamanho": len(conteudo)},
                posicao_inicio=posicao,
                posicao_fim=posicao + conteudo.count('\n')
            )
            chunks.append(chunk)
        else:
            # Dividir por sentenças para não cortar no meio
            sentencas = re.split(r'(?<=[.;:])\s+', conteudo)
            buffer = ""
            
            for sentenca in sentencas:
                if len(buffer) + len(sentenca) > self.max_chunk_size and buffer:
                    chunk = ChunkJuridico(
                        id=self._gerar_id(),
                        tipo=tipo,
                        conteudo=buffer.strip(),
                        hierarquia=hier_lista.copy(),
                        metadata={"fonte": fonte, "tamanho": len(buffer)},
                        posicao_inicio=posicao,
                        posicao_fim=posicao
                    )
                    chunks.append(chunk)
                    
                    # Overlap: manter últimas palavras
                    palavras = buffer.split()
                    overlap_text = ' '.join(palavras[-self.overlap:]) if len(palavras) > self.overlap else ""
                    buffer = overlap_text + " " + sentenca
                else:
                    buffer += (" " if buffer else "") + sentenca
            
            if buffer.strip():
                chunk = ChunkJuridico(
                    id=self._gerar_id(),
                    tipo=tipo,
                    conteudo=buffer.strip(),
                    hierarquia=hier_lista.copy(),
                    metadata={"fonte": fonte, "tamanho": len(buffer)},
                    posicao_inicio=posicao,
                    posicao_fim=posicao
                )
                chunks.append(chunk)
        
        return chunks
    
    def chunking_por_artigos(self, texto: str) -> List[ChunkJuridico]:
        """
        Chunking simplificado: cada artigo vira um chunk.
        Útil para documentos menores ou busca por artigo.
        """
        artigos = re.split(r'(?=Art\.\s*\d+)', texto)
        chunks = []
        
        for artigo in artigos:
            artigo = artigo.strip()
            if artigo:
                match = re.match(r'Art\.\s*(\d+)', artigo)
                ref = f"Art. {match.group(1)}" if match else "Preâmbulo"
                
                chunk = ChunkJuridico(
                    id=self._gerar_id(),
                    tipo=TipoElemento.ARTIGO if match else TipoElemento.PREAMBULO,
                    conteudo=artigo,
                    hierarquia=[ref],
                    metadata={"referencia": ref}
                )
                chunks.append(chunk)
        
        return chunks


# Exemplo de uso
if __name__ == "__main__":
    texto_exemplo = """
    TÍTULO I
    Disposições Preliminares
    
    Art. 1º Esta Lei regula os direitos e obrigações concernentes aos bens imóveis
    rurais, para os fins de execução da Reforma Agrária e promoção da Política Agrícola.
    
    § 1º Considera-se Reforma Agrária o conjunto de medidas que visem a promover
    melhor distribuição da terra, mediante modificações no regime de sua posse e uso.
    
    § 2º Entende-se por Política Agrícola o conjunto de providências de amparo à
    propriedade da terra.
    
    I - assistência técnica;
    II - produção e distribuição de sementes e mudas;
    III - criação, venda e distribuição de reprodutores e uso da inseminação artificial;
    
    a) cooperativismo;
    b) assistência financeira e creditícia;
    c) assistência à comercialização;
    
    Art. 2º É assegurada a todos a oportunidade de acesso à propriedade da terra,
    condicionada pela sua função social.
    """
    
    chunker = ChunkingJuridico(max_chunk_size=300)
    chunks = chunker.chunking_estrutural(texto_exemplo, fonte="Lei 4.504/64")
    
    for chunk in chunks:
        print(f"\n{'='*60}")
        print(f"ID: {chunk.id}")
        print(f"Tipo: {chunk.tipo.value}")
        print(f"Hierarquia: {' > '.join(chunk.hierarquia)}")
        print(f"Conteúdo: {chunk.conteudo[:100]}...")
