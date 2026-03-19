import io
from typing import Optional

class DocumentProcessor:
    """
    Processador de documentos para extrair texto de vários formatos.
    Suporta PDFs textuais, PDFs escaneados (OCR) e arquivos DOCX.
    """
    
    @staticmethod
    def extract_text(file_bytes: bytes, filename: str) -> str:
        """Extrai texto baseado na extensão do arquivo."""
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        
        if ext == 'pdf':
            return DocumentProcessor.extract_pdf(file_bytes)
        elif ext == 'docx':
            return DocumentProcessor.extract_docx(file_bytes)
        elif ext in ['txt', 'md']:
            return file_bytes.decode('utf-8', errors='replace')
        else:
            raise ValueError(f"Formato não suportado: {ext}")
            
    @staticmethod
    def extract_pdf(file_bytes: bytes) -> str:
        """
        Extrai texto de PDF usando pdfplumber.
        Tenta usar OCR (Tesseract) como fallback se o PDF for imagem escaneada.
        """
        text = ""
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
            
            # Se o texto for muito curto/vazio, é provável que seja um PDF escaneado (imagem)
            if len(text.strip()) < 50:
                print("PDF textual parece vazio. Tentando OCR para PDF escaneado...")
                text = DocumentProcessor._extract_pdf_ocr(file_bytes)
                if not text:
                    text = "[Aviso: Este PDF parece ser uma imagem escaneada. Processamento OCR falhou ou não encontrou texto.]"
                    
        except Exception as e:
            raise ValueError(f"Erro ao processar PDF: {str(e)}")
            
        return text
        
    @staticmethod
    def _extract_pdf_ocr(file_bytes: bytes) -> str:
        """Método de fallback usando pdf2image e pytesseract (OCR)."""
        text = ""
        try:
            from pdf2image import convert_from_bytes
            import pytesseract
            
            # Necessário conversor poppler instalado no sistema
            images = convert_from_bytes(file_bytes)
            for i, img in enumerate(images):
                print(f"Executando OCR na página {i+1}...")
                page_text = pytesseract.image_to_string(img, lang='por')
                text += page_text + "\n"
        except ImportError:
            print("Bibliotecas OCR não instaladas (pdf2image, pytesseract).")
        except Exception as e:
            print(f"Erro no OCR: {e}. O Tesseract e Poppler precisam estar instalados no SO.")
            
        return text

    @staticmethod
    def extract_docx(file_bytes: bytes) -> str:
        """Extrai texto de arquivos do Word (.docx)."""
        text = ""
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            for para in doc.paragraphs:
                text += para.text + "\n"
        except Exception as e:
            raise ValueError(f"Erro ao processar DOCX: {str(e)}")
            
        return text
