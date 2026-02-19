import streamlit as st
import PyPDF2
import io

def extrair_texto_pdf(arquivo_pdf):
    try:
        leitor = PyPDF2.PdfReader(arquivo_pdf)
        texto_acumulado = ""
        
        for i, pagina in enumerate(leitor.pages):
            conteudo = pagina.extract_text()
            if conteudo:
                texto_acumulado += f"--- Início da Página {i+1} ---\n"
                texto_acumulado += conteudo + "\n\n"
        
        return texto_acumulado
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
                    st.text_area("Prévia do Texto Extraído:", texto_extraido, height=300)
                    
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
