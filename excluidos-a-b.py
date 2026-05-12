import streamlit as st
import pandas as pd
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds

# Configuração da página
st.set_page_config(page_title="Excluídos de A e B", page_icon="logo.svg", layout="wide")

# Logo alinhado à esquerda com largura de 250px
st.image("logo.svg", width=250)

st.title("Excluídos de A e B")
st.write("Coloque um ficheiro Excel ou CSV com valores nas colunas A e B. A app identificará a maior soma comum e devolverá os elementos que ficaram de fora.")

# Função para limpar e preparar uma única coluna
def preparar_coluna(df, idx_coluna, nome_lista):
    # Extrai a coluna pelo índice
    try:
        col = df.iloc[:, idx_coluna].copy()
    except IndexError:
        return pd.DataFrame()

    # Cria um DataFrame temporário
    df_temp = pd.DataFrame({f'Valor {nome_lista}': col})
    
    # O TRITURADOR: limpa espaços e trata a vírgula decimal PT-PT
    df_temp['ValorNum'] = pd.to_numeric(
        df_temp[f'Valor {nome_lista}'].astype(str).str.replace(' ', '').str.replace(',', '.'), 
        errors='coerce'
    )
    
    # Remove zeros e NaNs
    df_temp = df_temp[df_temp['ValorNum'] != 0]
    df_limpo = df_temp.dropna(subset=['ValorNum']).reset_index(drop=True)
    return df_limpo

# Função do motor matemático
def otimizar_simples(df_A, df_B):
    A_vals = df_A['ValorNum'].tolist()
    B_vals = df_B['ValorNum'].tolist()

    # Conversão para inteiros (cêntimos) para precisão no solver
    A_ints = np.array([int(round(x * 100)) for x in A_vals])
    B_ints = np.array([int(round(x * 100)) for x in B_vals])

    n, m = len(A_ints), len(B_ints)

    if n == 0 or m == 0:
        return False, 0, n, m, pd.DataFrame()

    # Função objetivo: Maximizar a soma de A (usando coeficiente negativo para o solver milp)
    c = np.zeros(n + m)
    c[:n] = -A_ints

    # Restrição: Soma de A - Soma de B = 0
    A_eq = np.zeros((1, n + m))
    A_eq[0, :n] = A_ints
    A_eq[0, n:] = -B_ints

    constraints = LinearConstraint(A_eq, 0, 0)
    bounds = Bounds(np.zeros(n + m), np.ones(n + m))
    integrality = np.ones(n + m) # 1 para variáveis binárias

    res = milp(c=c, constraints=constraints, integrality=integrality, bounds=bounds)

    if res.success:
        x_res = np.round(res.x[:n])
        y_res = np.round(res.x[n:])
        
        soma_max = sum([A_vals[i] for i in range(n) if x_res[i] == 1])
        
        # Isolar os NÃO USADOS (onde a variável de decisão é 0)
        excluidos_A = df_A.loc[x_res == 0, [f'Valor A']].reset_index(drop=True)
        excluidos_B = df_B.loc[y_res == 0, [f'Valor B']].reset_index(drop=True)
        
        # Juntar lado a lado
        df_final = pd.concat([excluidos_A, excluidos_B], axis=1).fillna('')
        
        return True, soma_max, n, m, df_final
    else:
        return False, 0, n, m, pd.DataFrame()

# Upload do ficheiro
ficheiro = st.file_uploader("Upload do ficheiro (A na 1ª coluna, B na 2ª)", type=["xlsx", "csv", "xlsm"])

if ficheiro is not None:
    try:
        if ficheiro.name.endswith('.csv'):
            df_bruto = pd.read_csv(ficheiro, header=None)
        else:
            df_bruto = pd.read_excel(ficheiro, header=None)

        # Preparação das duas colunas base
        df_lista_A = preparar_coluna(df_bruto, 0, "A")
        df_lista_B = preparar_coluna(df_bruto, 1, "B")

        if not df_lista_A.empty and not df_lista_B.empty:
            with st.spinner("A calcular exclusões..."):
                sucesso, soma_comum, total_A, total_B, df_excluidos = otimizar_simples(df_lista_A, df_lista_B)
                
                if sucesso:
                    st.write("---")
                    st.subheader("Resultados da Análise")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Soma Comum Encontrada", f"{soma_comum:,.2f} €")
                    c2.metric("Elementos em A", total_A)
                    c3.metric("Elementos em B", total_B)

                    st.write(f"Foram identificados **{len(df_excluidos)}** linhas com elementos que não pertencem à soma comum.")

                    # Botão para descarregar
                    csv = df_excluidos.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Descarregar CSV de Excluídos",
                        data=csv,
                        file_name="Elementos_Excluidos_A_B.csv",
                        mime="text/csv"
                    )
                    
                    # Pré-visualização opcional
                    with st.expander("Ver lista de excluídos na app"):
                        st.table(df_excluidos.head(20))
                else:
                    st.error("Não foi possível encontrar uma combinação matemática válida.")
        else:
            st.warning("Certifique-se de que o ficheiro tem números válidos nas duas primeiras colunas.")

    except Exception as e:
        st.error(f"Erro ao processar ficheiro: {e}")
