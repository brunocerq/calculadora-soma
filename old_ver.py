import streamlit as st
import pandas as pd
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds

# Configuração da página
st.set_page_config(page_title="Calculadora de Soma Máxima", layout="centered")

# Usar o logótipo como ícone no separador do navegador
st.set_page_config(page_title="Calculadora de Soma Máxima", page_icon="logo.svg", layout="centered")

# Apresentar o logótipo no topo da página web
st.image("logo.svg", width=250)

st.title("Otimização: Maior Soma Comum de Dois Conjuntos")
st.write("Faça o carregamento de um ficheiro (CSV ou Excel) que contenha duas colunas nomeadas 'A' e 'B'. A aplicação irá descobrir quais os elementos de cada coluna que, somados, resultam no maior valor comum possível.")

# Zona de carregamento do ficheiro
ficheiro_carregado = st.file_uploader("Escolha o ficheiro", type=["csv", "xlsx", "xls", "xlsm"])

if ficheiro_carregado is not None:
    try:
        # Tentar ler o ficheiro consoante a extensão
        if ficheiro_carregado.name.endswith('.csv'):
            # Pode ser necessário ajustar o separador, ou o header dependendo do CSV
            df = pd.read_csv(ficheiro_carregado)
        else:
            df = pd.read_excel(ficheiro_carregado)
            
        # Verificar se as colunas necessárias existem
        if 'A' not in df.columns or 'B' not in df.columns:
            st.error("Atenção: O ficheiro deve obrigatoriamente conter as colunas 'A' e 'B'.")
        else:
            st.success("Ficheiro lido com sucesso! A iniciar o cálculo matemático...")
            
            # Mostrar indicação visual de processamento
            with st.spinner("A processar a otimização... isto pode demorar alguns segundos a minutos dependendo da quantidade de dados."):
                
                A_vals = df['A'].dropna().tolist()
                B_vals = df['B'].dropna().tolist()

                # Multiplicar por 100 para lidar com decimais e evitar erros de precisão do Python
                A_ints = np.array([int(round(x * 100)) for x in A_vals])
                B_ints = np.array([int(round(x * 100)) for x in B_vals])

                n = len(A_ints)
                m = len(B_ints)

                # Configuração do algoritmo MILP (Mixed-Integer Linear Programming)
                c = np.zeros(n + m)
                c[:n] = -A_ints

                A_eq = np.zeros((1, n + m))
                A_eq[0, :n] = A_ints
                A_eq[0, n:] = -B_ints

                bounds = Bounds(np.zeros(n + m), np.ones(n + m))
                integrality = np.ones(n + m)
                constraints = LinearConstraint(A_eq, 0, 0)

                # Executar a otimização
                res = milp(c=c, constraints=constraints, integrality=integrality, bounds=bounds)

                if res.success:
                    x_res = np.round(res.x[:n])
                    y_res = np.round(res.x[n:])
                    
                    selected_A = [A_vals[i] for i in range(n) if x_res[i] == 1]
                    selected_B = [B_vals[i] for i in range(m) if y_res[i] == 1]
                    
                    soma_A = sum(selected_A)
                    soma_B = sum(selected_B)
                    
                    # Mostrar resultados no ecrã
                    st.write("### Resultados da Otimização")
                    st.write(f"**Soma Máxima Encontrada:** {soma_A:.2f}")
                    st.write(f"**Elementos usados de A:** {len(selected_A)} (de um total de {n})")
                    st.write(f"**Elementos usados de B:** {len(selected_B)} (de um total de {m})")
                    
                    # Preparar os dados para o utilizador descarregar
                    max_len = max(len(selected_A), len(selected_B))
                    selected_A_padded = selected_A + [np.nan] * (max_len - len(selected_A))
                    selected_B_padded = selected_B + [np.nan] * (max_len - len(selected_B))
                    
                    df_out = pd.DataFrame({'Elementos de A': selected_A_padded, 'Elementos de B': selected_B_padded})
                    
                    # Converter o DataFrame para formato CSV
                    csv_buffer = df_out.to_csv(index=False).encode('utf-8')
                    
                    # Botão para descarregar o ficheiro final
                    st.download_button(
                        label="Descarregar Resultado (CSV)",
                        data=csv_buffer,
                        file_name="Soma_Maxima_Elementos.csv",
                        mime="text/csv"
                    )
                else:
                    st.error("Não foi possível encontrar uma solução ótima para os conjuntos fornecidos.")

    except Exception as e:

        st.error(f"Ocorreu um erro ao processar o ficheiro. Detalhe: {e}")
