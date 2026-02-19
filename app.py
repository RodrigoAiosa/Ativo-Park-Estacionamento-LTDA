import streamlit as st
import PyPDF2
import re

def extrair_texto_pdf(arquivo_pdf):
    try:
        leitor = PyPDF2.PdfReader(arquivo_pdf)
        texto_acumulado = ""
        
        padrao_emissao = r"Emissão Período.*Valores Lançados"
        padrao_detalhamento = r"DETALHAMENTO DAS TRANSAÇÕESRELATÓRIO DE TRANSAÇÕES"
        padrao_pagina = r"Página:\s*\d+\s*de\s*\d+"
        cabecalho_colunas = "Caixa V. Lançado Data Tarifa V. Estadia Ticket V. Abonado Transação T. Fiscais Sessão Abono Forma"

        for i in range(len(leitor.pages)):
            pagina = leitor.pages[i]
            conteudo = pagina.extract_text()
            
            if conteudo:
                conteudo = re.sub(padrao_emissao, "", conteudo, flags=re.DOTALL | re.IGNORECASE)
                conteudo = re.sub(padrao_detalhamento, "", conteudo, flags=re.IGNORECASE)
                conteudo = re.sub(padrao_pagina, "", conteudo, flags=re.IGNORECASE)
                conteudo = conteudo.replace(cabecalho_colunas, "")
                texto_acumulado += conteudo + "\n"

        linhas = [linha.strip() for linha in texto_acumulado.split('\n') if linha.strip()]
        return "\n".join(linhas)
    except Exception as e:
        st.error(f"Erro ao processar o PDF: {e}")
        return None

def main():
    st.set_page_config(page_title="Extrator de Dados PDF", page_icon="📄")
    st.title("📄 Extrator de Dados (Limpeza de Relatório)")
    st.write("Gere um arquivo .txt limpo, sem cabeçalhos e paginação.")

    # Inicializa o estado
    if 'texto_final' not in st.session_state:
        st.session_state.texto_final = None
    if 'nome_arquivo' not in st.session_state:
        st.session_state.nome_arquivo = None

    arquivo_carregado = st.file_uploader("Escolha o arquivo PDF", type="pdf")

    if arquivo_carregado:
        st.success(f"Arquivo '{arquivo_carregado.name}' carregado!")
        
        if st.button("Processar e Extrair Dados"):
            with st.spinner('Limpando e extraindo...'):
                resultado = extrair_texto_pdf(arquivo_carregado)
                if resultado:
                    st.session_state.texto_final = resultado
                    # ✅ Salva o nome do arquivo no session_state
                    st.session_state.nome_arquivo = arquivo_carregado.name.replace(".pdf", "_extraido.txt")
                    st.success("Processamento concluído!")

    # ✅ Renderiza prévia e botão fora do bloco do file_uploader
    if st.session_state.texto_final:
        st.text_area("Prévia dos dados limpos:", st.session_state.texto_final, height=250)
        
        st.download_button(
            label="📥 Baixar arquivo .txt",
            data=st.session_state.texto_final,
            file_name=st.session_state.nome_arquivo,
            mime="text/plain"
        )

if __name__ == "__main__":
    main()
