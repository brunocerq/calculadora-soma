import streamlit as st
import pandas as pd
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds

st.set_page_config(page_title="Calculadora de Soma Máxima", page_icon="logo.svg", layout="centered")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image("logo.svg", use_container_width=True)

st.title("Otimização: Maior Soma Comum de Dois Conjuntos - V3")
st.write("A aplicação irá procurar as colunas 'A' e 'B', ou em alternativa, os dados nas colunas AA e AB do seu Excel.")

ficheiro_carregado = st.file_uploader("Escolha o ficheiro", type=["csv", "xlsx", "xls", "xlsm"])

if ficheiro_carregado is not None:
    try:
        if ficheiro_carregado.name.endswith('.csv'):
            df = pd.read_csv(ficheiro_carregado, header=None) # Ajustado para ler a grelha bruta
        else:
            df = pd.read_excel(ficheiro_carregado, header=None)
            
        col_A_data = None
        col_B_data = None
        
        # O Pandas, lendo com header=None, coloca as colunas reais nas linhas. 
        # Vamos procurar a linha onde estão o 'A' e 'B' ou assumir posições físicas
        
        # PLANO B Principal: Ler as colunas físicas AA (índice 26) e AB (índice 27)
        if df.shape[1] >= 28:
            col_A_data = df.iloc[:, 26]
            col_B_data = df.iloc[:, 27]
        # PLANO A Alternativo: O ficheiro antigo onde A e B estão logo no início (índice 0 e 1)
        elif df.shape[1] >= 2:
            col_A_data = df.iloc[:, 0]
            col_B_data = df.iloc[:, 1]
            
        if col_A_data is None or col_B_data is None:
            st.error("Atenção: O ficheiro não possui colunas suficientes para ler os dados.")
        else:
            st.success("Ficheiro validado! A iniciar o cálculo matemático...")
            
            with st.spinner("A processar a otimização... isto pode demorar alguns segundos a minutos dependendo da quantidade de dados."):
                
                # --- O TRITURADOR (Limpeza e formatação PT-PT) ---
                col_A_limpa = pd.to_numeric(col_A_data.astype(str).str.replace(',', '.'), errors='coerce').dropna()
                col_B_limpa = pd.to_numeric(col_B_data.astype(str).str.replace(',', '.'), errors='coerce').dropna()
                
                A_vals = col_A_limpa.tolist()
                B_vals = col_B_limpa.tolist()

                A_ints = np.array([int(round(x * 100)) for x in A_vals])
                B_ints = np.array([int(round(x * 100)) for x in B_vals])

                n = len(A_ints)
                m = len(B_ints)

                if n == 0 or m == 0:
                    st.warning("Não existem números válidos suficientes nas colunas selecionadas para realizar a otimização.")
                else:
                    c = np.zeros(n + m)
                    c[:n] = -A_ints

                    A_eq = np.zeros((1, n + m))
                    A_eq[0, :n] = A_ints
                    A_eq[0, n:] = -B_ints

                    bounds = Bounds(np.zeros(n + m), np.ones(n + m))
                    integrality = np.ones(n + m)
                    constraints = LinearConstraint(A_eq, 0, 0)

                    res = milp(c=c, constraints=constraints, integrality=integrality, bounds=bounds)

                    if res.success:
                        x_res = np.round(res.x[:n])
                        y_res = np.round(res.x[n:])
                        
                        selected_A = [A_vals[i] for i in range(n) if x_res[i] == 1]
                        selected_B = [B_vals[i] for i in range(m) if y_res[i] == 1]
                        
                        soma_A = sum(selected_A)
                        soma_B = sum(selected_B)
                        
                        st.write("### Resultados da Otimização")
                        st.write(f"**Soma Máxima Encontrada:** {soma_A:.2f}")
                        st.write(f"**Elementos usados da primeira lista:** {len(selected_A)} (de um total de {n})")
                        st.write(f"**Elementos usados da segunda lista:** {len(selected_B)} (de um total de {m})")
                        
                        max_len = max(len(selected_A), len(selected_B))
                        selected_A_padded = selected_A + [np.nan] * (max_len - len(selected_A))
                        selected_B_padded = selected_B + [np.nan] * (max_len - len(selected_B))
                        
                        df_out = pd.DataFrame({'Elementos Lista 1': selected_A_padded, 'Elementos Lista 2': selected_B_padded})
                        
                        csv_buffer = df_out.to_csv(index=False).encode('utf-8')
                        
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
