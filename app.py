import streamlit as st
import PyPDF2
import io
import re

def extrair_texto_pdf(arquivo_pdf):
    try:
        leitor = PyPDF2.PdfReader(arquivo_pdf)
        texto_acumulado = ""
        
        for i, pagina in enumerate(leitor.pages):
            conteudo = pagina.extract_text()
            if conteudo:
                # 1. Remover o cabeçalho específico de Emissão e Transações
                conteudo = re.sub(r"Emissão Período.*Values Lançados", "", conteudo, flags=re.DOTALL)
                conteudo = re.sub(r"DETALHAMENTO DAS TRANSAÇÕESRELATÓRIO DE TRANSAÇÕES", "", conteudo)
                
                # 2. Remover "Página: X de Y"
                conteudo = re.sub(r"Página:\s*\d+\s*de\s*\d+", "", conteudo)
                
                # 3. Remover o cabeçalho das colunas (Caixa, V. Lançado, etc.)
                cabecalho_colunas = "Caixa V. Lançado Data Tarifa V. Estadia Ticket V. Abonado Transação T. Fiscais Sessão Abono Forma"
                conteudo = conteudo.replace(cabecalho_colunas, "")
                
                texto_acumulado += conteudo + "\n"
        
        # Limpeza final de espaços em branco excessivos
        texto_limpo = "\n".join([linha.strip() for linha in texto_acumulado.split('\n') if linha.strip()])
        
        return texto_limpo
    except Exception as e:
        st.error(f"Erro ao processar o PDF: {e}")
        return None

def main():
    st.set_page_config(page_title="Extrator de PDF para TXT", page_icon="📄")
    
    st.title("📄 Extrator de PDF para Texto")
    st.write("Faça o upload de um arquivo PDF para extrair seu conteúdo e baixar como TXT.")

    # Componente de Upload
    arquivo_carregado = st.file_uploader("Escolha o arquivo PDF", type="pdf")

    if arquivo_carregado is not None:
        st.success(f"Arquivo '{arquivo_carregado.name}' carregado com sucesso!")
        
        # Botão para processar
        if st.button("Extrair Texto"):
            with st.spinner('Extraindo dados...'):
                texto_extraido = extrair_texto_pdf(arquivo_carregado)
                
                if texto_extraido:
                    st.text_area("Prévia do Texto Extraído (Limpo):", texto_extraido, height=300)
                    
                    # Preparar download
                    nome_arquivo_txt = arquivo_carregado.name.replace(".pdf", "_extraido.txt")
                    
                    st.download_button(
                        label="📥 Baixar arquivo .txt",
                        data=texto_extraido,
                        file_name=nome_arquivo_txt,
                        mime="text/plain"
                    )

if __name__ == "__main__":
    main()
