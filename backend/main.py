"""
LexAI — Servidor FastAPI do Assistente Jurídico

API REST + Servir Frontend estático.
Deploy unificado: backend + frontend em um único serviço.
"""

import os
import json
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

from modules.assistant import JuridicAssistant
from modules.document_processor import DocumentProcessor

# ═══════════════════════════════════════════════════
# App Configuration
# ═══════════════════════════════════════════════════

app = FastAPI(
    title="LexAI — Assistente Jurídico com IA",
    description="API para análise, correção e consulta de documentos jurídicos brasileiros.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS - permitir acesso de qualquer origem
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar assistente
assistant = JuridicAssistant(top_k=5, mascarar_lgpd=True)


# ═══════════════════════════════════════════════════
# Request/Response Models
# ═══════════════════════════════════════════════════

class ConsultaRequest(BaseModel):
    query: str = Field(..., description="Consulta jurídica em linguagem natural")
    top_k: int = Field(5, description="Número de documentos relevantes")

class DocumentoRequest(BaseModel):
    texto: str = Field(..., description="Texto do documento jurídico")
    fonte: str = Field("", description="Identificação da fonte")

class CorrecaoRequest(BaseModel):
    texto: str = Field(..., description="Texto para correção gramatical")

class EntidadesRequest(BaseModel):
    texto: str = Field(..., description="Texto para extração de entidades")

class AdicionarDocumentoRequest(BaseModel):
    documentos: List[Dict[str, str]] = Field(..., description="Lista de documentos")


# ═══════════════════════════════════════════════════
# API Endpoints (prefixados com /api)
# ═══════════════════════════════════════════════════

@app.get("/api")
async def api_root():
    """Informações da API."""
    return {
        "nome": "LexAI — Assistente Jurídico com IA",
        "versao": "1.0.0",
        "descricao": "API para análise e consulta de documentos jurídicos",
        "endpoints": {
            "/api/consultar": "POST - Consulta jurídica completa",
            "/api/analisar": "POST - Análise de documento jurídico",
            "/api/corrigir": "POST - Correção gramatical jurídica",
            "/api/entidades": "POST - Extração de entidades jurídicas",
            "/api/documentos": "POST - Adicionar documentos à base",
            "/api/estatisticas": "GET - Estatísticas do sistema",
            "/api/historico": "GET - Histórico de consultas",
            "/api/docs": "GET - Documentação interativa (Swagger)"
        }
    }


@app.post("/api/consultar")
async def consultar(request: ConsultaRequest):
    """Consulta jurídica completa."""
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query não pode ser vazia")
        assistant.top_k = request.top_k
        resposta = assistant.consultar(request.query)
        return JSONResponse(content=resposta.to_dict(), status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analisar")
async def analisar(request: DocumentoRequest):
    """Analisa documento jurídico."""
    try:
        if not request.texto.strip():
            raise HTTPException(status_code=400, detail="Texto não pode ser vazio")
        resultado = assistant.analisar_documento(request.texto, fonte=request.fonte)
        return JSONResponse(content=resultado, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/corrigir")
async def corrigir(request: CorrecaoRequest):
    """Correção gramatical jurídica."""
    try:
        texto_corrigido, correcoes = assistant.grammar.corrigir(request.texto)
        resumo = assistant.grammar.resumo_correcoes(correcoes)
        return {
            "texto_original": request.texto,
            "texto_corrigido": texto_corrigido,
            "correcoes": [c.to_dict() for c in correcoes],
            "resumo": resumo
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/entidades")
async def entidades(request: EntidadesRequest):
    """Extrai entidades jurídicas."""
    try:
        entidades = assistant.entity_extractor.extrair(request.texto)
        resumo = assistant.entity_extractor.resumo_entidades(entidades)
        referencias = assistant.entity_extractor.extrair_referencias_cruzadas(request.texto)
        return {
            "entidades": [e.to_dict() for e in entidades],
            "resumo": resumo,
            "referencias_cruzadas": referencias,
            "total": len(entidades)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/documentos")
async def adicionar_documentos(request: AdicionarDocumentoRequest):
    """Adiciona documentos à base de conhecimento."""
    try:
        total = assistant.adicionar_documentos(request.documentos)
        return {
            "mensagem": f"{len(request.documentos)} documento(s) adicionado(s)",
            "total_base": total
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload")
async def upload_documento(file: UploadFile = File(...)):
    """Upload de documento para análise e extração de texto (PDF, DOCX, TXT)."""
    try:
        conteudo = await file.read()
        filename = file.filename or "upload.txt"
        
        # Processa o binário e extrai o texto com OCR/pdfplumber ou docx
        texto = DocumentProcessor.extract_text(conteudo, filename)
        
        # Analisa documento com assistente
        resultado = assistant.analisar_documento(texto, fonte=filename)
        num_chunks = assistant.adicionar_documento_texto(texto, fonte=filename)
        resultado["chunks_adicionados"] = num_chunks
        
        return JSONResponse(content=resultado, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/estatisticas")
async def estatisticas():
    """Estatísticas do sistema."""
    return assistant.estatisticas()


@app.get("/api/historico")
async def historico():
    """Histórico de consultas da sessão."""
    return {
        "total": len(assistant.historico),
        "consultas": [r.to_dict() for r in assistant.historico[-20:]]
    }


@app.get("/api/saude")
async def saude():
    """Health check endpoint."""
    return {"status": "ok", "servico": "LexAI", "versao": "1.0.0"}


# ═══════════════════════════════════════════════════
# Servir Frontend Estático
# ═══════════════════════════════════════════════════

# Caminho para os arquivos do frontend
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")

# Montar diretórios estáticos (CSS, JS)
if os.path.exists(os.path.join(FRONTEND_DIR, "css")):
    app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")

if os.path.exists(os.path.join(FRONTEND_DIR, "js")):
    app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")


@app.get("/")
async def serve_frontend():
    """Servir o index.html do frontend."""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"mensagem": "LexAI API ativa. Frontend não encontrado.", "docs": "/api/docs"}


# ═══════════════════════════════════════════════════
# Run Server
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    
    print("🏛️ LexAI — Assistente Jurídico com IA")
    print("=" * 50)
    print(f"📡 Servidor: http://localhost:{port}")
    print(f"📖 API Docs: http://localhost:{port}/api/docs")
    print(f"🌐 Frontend: http://localhost:{port}")
    print("=" * 50)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
