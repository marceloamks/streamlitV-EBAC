import pandas as pd
import streamlit as st
import numpy as np
from datetime import datetime
from PIL import Image
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go

# Configuração da página
st.set_page_config(page_title="Análise RFV", page_icon="📊", layout="wide")

# Título principal
st.title("📊 Análise RFV - Recência, Frequência e Valor")
st.markdown("---")

# Função para criar dados de exemplo
@st.cache_data
def gerar_dados_exemplo():
    np.random.seed(42)
    n_clientes = 1000

    datas = pd.date_range(start='2023-01-01', end='2024-12-31', freq='D')

    dados = {
        'cliente_id': np.random.choice(range(1, 201), n_clientes),
        'data_compra': np.random.choice(datas, n_clientes),
        'valor_compra': np.random.uniform(50, 1000, n_clientes).round(2)
    }

    df = pd.DataFrame(dados)
    df['data_compra'] = pd.to_datetime(df['data_compra'])
    return df

# Função para mapear colunas
def mapear_colunas(df):
    """Tenta identificar automaticamente as colunas de cliente, data e valor"""
    colunas_cliente = ['cliente_id', 'id_cliente', 'cliente', 'customer_id', 'customer', 'id',
                       'cod_cliente', 'codigo_cliente', 'cdcliente', 'cd_cliente',
                       'num_cliente', 'nr_cliente', 'ID_cliente', 'ID_CLIENTE']

    colunas_data = ['data_compra', 'dt_compra', 'data', 'date', 'data_pedido', 'dt_pedido',
                    'data_venda', 'dt_venda', 'data_transacao', 'dt_transacao',
                    'data_nota', 'dt_nota', 'DiaCompra', 'DATA_COMPRA']

    colunas_valor = ['valor_compra', 'vl_compra', 'valor', 'value', 'total', 'vl_total',
                     'valor_total', 'preco', 'amount', 'receita', 'vl_pedido',
                     'valor_pedido', 'vl_nota', 'valor_nota', 'ValorTotal', 'VALOR_TOTAL']

    # Normaliza para comparação case-insensitive
    colunas_df = {col: col for col in df.columns}
    colunas_df_lower = {col.lower(): col for col in df.columns}

    mapeamento = {}

    for col in colunas_cliente:
        if col in colunas_df:
            mapeamento['cliente_id'] = col
            break
        if col.lower() in colunas_df_lower:
            mapeamento['cliente_id'] = colunas_df_lower[col.lower()]
            break

    for col in colunas_data:
        if col in colunas_df:
            mapeamento['data_compra'] = col
            break
        if col.lower() in colunas_df_lower:
            mapeamento['data_compra'] = colunas_df_lower[col.lower()]
            break

    for col in colunas_valor:
        if col in colunas_df:
            mapeamento['valor_compra'] = col
            break
        if col.lower() in colunas_df_lower:
            mapeamento['valor_compra'] = colunas_df_lower[col.lower()]
            break

    return mapeamento

# Sidebar para upload de dados
st.sidebar.header("📁 Carregar Dados")
tipo_dados = st.sidebar.radio(
    "Selecione a origem dos dados:",
    ["Dados de Exemplo", "Upload de Arquivo"]
)

df = None  # inicializa df

if tipo_dados == "Dados de Exemplo":
    df = gerar_dados_exemplo()
    st.sidebar.success("✅ Usando dados de exemplo")
else:
    uploaded_file = st.sidebar.file_uploader(
        "Escolha um arquivo CSV",
        type="csv",
        help="O arquivo deve conter colunas para ID do cliente, data da compra e valor"
    )

    if uploaded_file is not None:
        try:
            try:
                df = pd.read_csv(uploaded_file, encoding='utf-8')
            except Exception:
                try:
                    df = pd.read_csv(uploaded_file, encoding='latin1')
                except Exception:
                    df = pd.read_csv(uploaded_file, encoding='ISO-8859-1')

            if df.empty:
                st.sidebar.error("❌ O arquivo está vazio")
                st.stop()

            st.sidebar.success(f"✅ Arquivo carregado! {len(df)} linhas encontradas")

            st.sidebar.subheader("📋 Colunas encontradas:")
            st.sidebar.write(df.columns.tolist())

            mapeamento = mapear_colunas(df)

            colunas_faltantes = []
            if 'cliente_id' not in mapeamento:
                colunas_faltantes.append('ID do Cliente')
            if 'data_compra' not in mapeamento:
                colunas_faltantes.append('Data da Compra')
            if 'valor_compra' not in mapeamento:
                colunas_faltantes.append('Valor da Compra')

            if colunas_faltantes:
                st.sidebar.error(f"❌ Colunas não encontradas: {', '.join(colunas_faltantes)}")
                st.sidebar.info("""
                **Colunas esperadas:**
                - ID do Cliente (ex: cliente_id, customer_id, id)
                - Data da Compra (ex: data_compra, date, dt_compra)
                - Valor da Compra (ex: valor_compra, value, total)
                """)

                st.sidebar.subheader("🔧 Mapeamento Manual")
                col_cliente = st.sidebar.selectbox("Coluna do Cliente:", df.columns)
                col_data = st.sidebar.selectbox("Coluna da Data:", df.columns)
                col_valor = st.sidebar.selectbox("Coluna do Valor:", df.columns)

                mapeamento = {
                    'cliente_id': col_cliente,
                    'data_compra': col_data,
                    'valor_compra': col_valor
                }

            df = df.rename(columns={
                mapeamento['cliente_id']: 'cliente_id',
                mapeamento['data_compra']: 'data_compra',
                mapeamento['valor_compra']: 'valor_compra'
            })

            df = df[['cliente_id', 'data_compra', 'valor_compra']]

            try:
                df['data_compra'] = pd.to_datetime(df['data_compra'])
            except Exception as e:
                st.sidebar.error(f"❌ Erro ao converter datas: {str(e)}")
                st.sidebar.info("Formatos aceitos: YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY")
                st.stop()

            try:
                df['valor_compra'] = pd.to_numeric(df['valor_compra'], errors='coerce')
                df = df.dropna(subset=['valor_compra'])
                if df.empty:
                    st.sidebar.error("❌ Nenhum valor válido encontrado na coluna de valor")
                    st.stop()
            except Exception:
                st.sidebar.error("❌ Erro ao converter valores. Verifique se a coluna contém números")
                st.stop()

            df = df.dropna()
            df = df.drop_duplicates()

            st.sidebar.success(f"✅ Dados processados: {len(df)} registros válidos")

        except Exception as e:
            st.sidebar.error(f"❌ Erro ao processar arquivo: {str(e)}")
            st.stop()
    else:
        st.sidebar.warning("⚠️ Por favor, faça upload de um arquivo CSV")
        st.info("""
### 📋 Instruções:

Seu arquivo CSV deve conter pelo menos 3 colunas:
- **ID do Cliente**: Identificador único do cliente
- **Data da Compra**: Data em que a compra foi realizada
- **Valor da Compra**: Valor monetário da compra

### 📁 Exemplo de arquivo:
```
cliente_id,data_compra,valor_compra
1,2024-01-15,150.00
1,2024-02-20,200.00
2,2024-01-10,300.00
```
""")
        st.stop()

# --- A partir daqui df está garantidamente carregado ---

# Parâmetros para análise
st.sidebar.header("⚙️ Configurações")
data_referencia = st.sidebar.date_input(
    "Data de Referência para Recência",
    value=df['data_compra'].max().date() + pd.Timedelta(days=1),
    help="Data base para calcular há quantos dias foi a última compra"
)
data_referencia = pd.to_datetime(data_referencia)

# Resumo dos dados
st.sidebar.subheader("📊 Resumo dos Dados")
st.sidebar.metric("Total de Registros", len(df))
st.sidebar.metric("Clientes Únicos", df['cliente_id'].nunique())
st.sidebar.metric("Período", f"{df['data_compra'].min().date()} a {df['data_compra'].max().date()}")

# Cálculo do RFV
@st.cache_data
def calcular_rfv(df, data_referencia):
    rfv_df = df.groupby('cliente_id').agg(
        **{
            'Recência (R)': ('data_compra', lambda x: (data_referencia - x.max()).days),
            'Frequência (F)': ('cliente_id', 'count'),
            'Valor (V)': ('valor_compra', 'sum'),
        }
    ).reset_index()
    return rfv_df

rfv_df = calcular_rfv(df, data_referencia)

# Cálculo dos quartis
@st.cache_data
def calcular_quartis(rfv_df):
    r_labels = [4, 3, 2, 1]
    f_labels = [1, 2, 3, 4]
    v_labels = [1, 2, 3, 4]

    rfv_segmentado = rfv_df.copy()

    try:
        rfv_segmentado['R_Quartil'] = pd.qcut(rfv_segmentado['Recência (R)'], q=4, labels=r_labels, duplicates='drop')
        rfv_segmentado['F_Quartil'] = pd.qcut(rfv_segmentado['Frequência (F)'], q=4, labels=f_labels, duplicates='drop')
        rfv_segmentado['V_Quartil'] = pd.qcut(rfv_segmentado['Valor (V)'], q=4, labels=v_labels, duplicates='drop')

        rfv_segmentado['RFV_Score'] = (
            rfv_segmentado['R_Quartil'].astype(str) +
            rfv_segmentado['F_Quartil'].astype(str) +
            rfv_segmentado['V_Quartil'].astype(str)
        )
    except Exception:
        st.warning("Alguns quartis podem não ter sido calculados perfeitamente devido à distribuição dos dados. Usando método alternativo.")
        rfv_segmentado['R_Quartil'] = pd.qcut(rfv_segmentado['Recência (R)'].rank(method='first'), q=4, labels=r_labels)
        rfv_segmentado['F_Quartil'] = pd.qcut(rfv_segmentado['Frequência (F)'].rank(method='first'), q=4, labels=f_labels)
        rfv_segmentado['V_Quartil'] = pd.qcut(rfv_segmentado['Valor (V)'].rank(method='first'), q=4, labels=v_labels)

        rfv_segmentado['RFV_Score'] = (
            rfv_segmentado['R_Quartil'].astype(str) +
            rfv_segmentado['F_Quartil'].astype(str) +
            rfv_segmentado['V_Quartil'].astype(str)
        )

    return rfv_segmentado

rfv_segmentado = calcular_quartis(rfv_df)

# Classificação de segmentos
def classificar_segmento(rfv_score):
    score_str = str(rfv_score)

    if score_str >= "444":
        return "🌟 Melhores Clientes"
    elif score_str >= "344":
        return "⭐ Clientes Fiéis"
    elif score_str >= "244":
        return "💪 Potenciais Fidelizados"
    elif score_str >= "144":
        return "🆕 Novos Clientes"
    elif score_str >= "443":
        return "⚠️ Clientes em Risco"
    elif score_str >= "333":
        return "💤 Clientes Adormecidos"
    elif score_str >= "222":
        return "📉 Quase Perdidos"
    else:
        return "❌ Clientes Perdidos"

rfv_segmentado['Segmento'] = rfv_segmentado['RFV_Score'].apply(classificar_segmento)

# Layout principal
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 Tabelas RFV",
    "📊 Segmentação",
    "👥 Grupos RFV",
    "🎯 Melhores Clientes",
    "📈 Ações de Marketing"
])

with tab1:
    st.header("Tabelas RFV")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Recência (R)")
        recencia_df = rfv_df[['cliente_id', 'Recência (R)']].sort_values('Recência (R)')
        st.dataframe(recencia_df.head(10), use_container_width=True)
        st.metric("Média de Recência", f"{rfv_df['Recência (R)'].mean():.0f} dias")

    with col2:
        st.subheader("Frequência (F)")
        frequencia_df = rfv_df[['cliente_id', 'Frequência (F)']].sort_values('Frequência (F)', ascending=False)
        st.dataframe(frequencia_df.head(10), use_container_width=True)
        st.metric("Média de Frequência", f"{rfv_df['Frequência (F)'].mean():.1f}")

    with col3:
        st.subheader("Valor (V)")
        valor_df = rfv_df[['cliente_id', 'Valor (V)']].sort_values('Valor (V)', ascending=False)
        st.dataframe(valor_df.head(10), use_container_width=True)
        st.metric("Valor Médio", f"R$ {rfv_df['Valor (V)'].mean():.2f}")

    st.markdown("---")
    st.subheader("Tabela RFV Final")
    st.dataframe(rfv_df.sort_values('cliente_id'), use_container_width=True)

with tab2:
    st.header("Segmentação utilizando o RFV")
    st.subheader("Quartis para o RFV")

    quartis_display = pd.DataFrame({
        'Métrica': ['Recência (R)', 'Frequência (F)', 'Valor (V)'],
        'Q1 (25%)': [
            f"{rfv_df['Recência (R)'].quantile(0.25):.0f} dias",
            f"{rfv_df['Frequência (F)'].quantile(0.25):.1f} compras",
            f"R$ {rfv_df['Valor (V)'].quantile(0.25):.2f}"
        ],
        'Q2 (50%)': [
            f"{rfv_df['Recência (R)'].quantile(0.50):.0f} dias",
            f"{rfv_df['Frequência (F)'].quantile(0.50):.1f} compras",
            f"R$ {rfv_df['Valor (V)'].quantile(0.50):.2f}"
        ],
        'Q3 (75%)': [
            f"{rfv_df['Recência (R)'].quantile(0.75):.0f} dias",
            f"{rfv_df['Frequência (F)'].quantile(0.75):.1f} compras",
            f"R$ {rfv_df['Valor (V)'].quantile(0.75):.2f}"
        ]
    })

    st.table(quartis_display)
    st.markdown("---")
    st.subheader("Tabela após a criação dos grupos")
    st.dataframe(rfv_segmentado.sort_values('RFV_Score', ascending=False), use_container_width=True)

with tab3:
    st.header("Quantidade de Clientes por Grupos")

    segmento_counts = rfv_segmentado['Segmento'].value_counts().reset_index()
    segmento_counts.columns = ['Segmento', 'Quantidade']

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Distribuição por Segmento")
        st.dataframe(segmento_counts, use_container_width=True)
        st.metric("Total de Clientes", len(rfv_segmentado))

    with col2:
        if not segmento_counts.empty:
            fig_pie = px.pie(
                segmento_counts,
                values='Quantidade',
                names='Segmento',
                title='Distribuição de Clientes por Segmento',
                hole=0.3
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    if not segmento_counts.empty:
        fig_bar = px.bar(
            segmento_counts,
            x='Segmento',
            y='Quantidade',
            title='Quantidade de Clientes por Segmento',
            color='Segmento',
            text='Quantidade'
        )
        fig_bar.update_traces(textposition='outside')
        st.plotly_chart(fig_bar, use_container_width=True)

with tab4:
    st.header("Clientes com Menor Recência, Maior Frequência e Maior Valor Gasto")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("🔝 Menor Recência")
        top_recencia = rfv_df.nsmallest(10, 'Recência (R)')[['cliente_id', 'Recência (R)']]
        st.dataframe(top_recencia, use_container_width=True)

    with col2:
        st.subheader("🔝 Maior Frequência")
        top_frequencia = rfv_df.nlargest(10, 'Frequência (F)')[['cliente_id', 'Frequência (F)']]
        st.dataframe(top_frequencia, use_container_width=True)

    with col3:
        st.subheader("🔝 Maior Valor")
        top_valor = rfv_df.nlargest(10, 'Valor (V)')[['cliente_id', 'Valor (V)']]
        st.dataframe(top_valor, use_container_width=True)

    st.markdown("---")
    st.subheader("🏆 Top 10 Clientes Ideais (RFV Score)")

    rfv_df['RFV_Ponderado'] = (
        (1 / rfv_df['Recência (R)'].clip(lower=1)).rank(pct=True) * 0.3 +
        rfv_df['Frequência (F)'].rank(pct=True) * 0.3 +
        rfv_df['Valor (V)'].rank(pct=True) * 0.4
    )

    top_rfv = rfv_df.nlargest(10, 'RFV_Ponderado')[
        ['cliente_id', 'Recência (R)', 'Frequência (F)', 'Valor (V)', 'RFV_Ponderado']
    ]

    top_rfv_display = top_rfv.copy()
    top_rfv_display['Valor (V)'] = top_rfv_display['Valor (V)'].apply(lambda x: f'R$ {x:.2f}')
    top_rfv_display['RFV_Ponderado'] = top_rfv_display['RFV_Ponderado'].apply(lambda x: f'{x:.3f}')

    st.dataframe(top_rfv_display, use_container_width=True)

with tab5:
    st.header("📈 Ações de Marketing/CRM")

    acoes_marketing = {
        "🌟 Melhores Clientes": {
            "Estratégia": "Fidelização e Exclusividade",
            "Ações": [
                "Programa VIP com benefícios exclusivos",
                "Acesso antecipado a novos produtos",
                "Convites para eventos especiais",
                "Programa de embaixadores da marca",
                "Atendimento personalizado premium"
            ],
            "Canais": "E-mail marketing personalizado, Telefone, App exclusivo",
            "Frequência": "Mensal"
        },
        "⭐ Clientes Fiéis": {
            "Estratégia": "Manutenção e Upsell",
            "Ações": [
                "Programa de pontos e recompensas",
                "Ofertas de upgrade de produtos/serviços",
                "Cross-selling de produtos complementares",
                "Pesquisas de satisfação com benefícios",
                "Clube de vantagens"
            ],
            "Canais": "E-mail marketing, App, SMS",
            "Frequência": "Quinzenal"
        },
        "💪 Potenciais Fidelizados": {
            "Estratégia": "Engajamento e Incentivo",
            "Ações": [
                "Ofertas de fidelização (descontos progressivos)",
                "Programa 'indique um amigo'",
                "Conteúdo educativo sobre produtos",
                "Desafios e gamificação",
                "Benefícios por recorrência de compra"
            ],
            "Canais": "E-mail marketing, Redes sociais, Notificações",
            "Frequência": "Semanal"
        },
        "🆕 Novos Clientes": {
            "Estratégia": "Onboarding e Educação",
            "Ações": [
                "Sequência de boas-vindas por e-mail",
                "Tutoriais e guias de uso dos produtos",
                "Primeiro desconto em próxima compra",
                "Apresentação do programa de fidelidade",
                "Pesquisa de perfil e preferências"
            ],
            "Canais": "E-mail marketing, WhatsApp, App",
            "Frequência": "Diária (primeira semana)"
        },
        "⚠️ Clientes em Risco": {
            "Estratégia": "Reativação e Retenção",
            "Ações": [
                "Ofertas exclusivas de retorno",
                "Desconto progressivo por tempo sem compra",
                "Pesquisa de motivo de afastamento",
                "Comparativo do que estão perdendo",
                "Atendimento proativo (SAC)"
            ],
            "Canais": "E-mail marketing, SMS, Telefone",
            "Frequência": "Semanal"
        },
        "💤 Clientes Adormecidos": {
            "Estratégia": "Reconquista",
            "Ações": [
                "Campanha 'sentimos sua falta'",
                "Ofertas agressivas de retorno",
                "Brindes ou amostras grátis",
                "Condições especiais de pagamento",
                "Pesquisa de feedback com incentivo"
            ],
            "Canais": "E-mail marketing, Mala direta, Telefone",
            "Frequência": "Quinzenal"
        },
        "📉 Quase Perdidos": {
            "Estratégia": "Resgate Urgente",
            "Ações": [
                "Oferta irrecusável de última chance",
                "Contato direto da gerência",
                "Pesquisa detalhada de insatisfação",
                "Condições exclusivas de renegociação",
                "Convite para evento de relacionamento"
            ],
            "Canais": "Telefone, E-mail, WhatsApp",
            "Frequência": "Semanal"
        },
        "❌ Clientes Perdidos": {
            "Estratégia": "Análise e Recuperação de Baixo Custo",
            "Ações": [
                "Campanha sazonal de reativação",
                "Pesquisa de mercado (motivo da perda)",
                "Ofertas em datas comemorativas",
                "Newsletter informativa (sem venda direta)",
                "Convite para novos produtos/serviços"
            ],
            "Canais": "E-mail marketing, Redes sociais",
            "Frequência": "Mensal"
        }
    }

    segmentos_disponiveis = list(acoes_marketing.keys())
    segmento_selecionado = st.selectbox(
        "Selecione um segmento para ver detalhes:",
        segmentos_disponiveis
    )

    if segmento_selecionado:
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown(f"### {segmento_selecionado}")
            info = acoes_marketing[segmento_selecionado]
            st.markdown(f"**🎯 Estratégia Principal:** {info['Estratégia']}")
            st.markdown(f"**📱 Canais Recomendados:** {info['Canais']}")
            st.markdown(f"**⏰ Frequência Ideal:** {info['Frequência']}")
            st.markdown("**✅ Ações Específicas:**")
            for i, acao in enumerate(info['Ações'], 1):
                st.markdown(f"{i}. {acao}")

        with col2:
            qtd_segmento = len(rfv_segmentado[rfv_segmentado['Segmento'] == segmento_selecionado])
            percentual = (qtd_segmento / len(rfv_segmentado)) * 100 if len(rfv_segmentado) > 0 else 0
            st.metric("Clientes no Segmento", qtd_segmento)
            st.metric("Representatividade", f"{percentual:.1f}%")

            segmento_data = rfv_segmentado[rfv_segmentado['Segmento'] == segmento_selecionado]
            if not segmento_data.empty:
                st.metric("Recência Média", f"{segmento_data['Recência (R)'].mean():.0f} dias")
                st.metric("Frequência Média", f"{segmento_data['Frequência (F)'].mean():.1f}")
                st.metric("Valor Médio", f"R$ {segmento_data['Valor (V)'].mean():.2f}")

    st.markdown("---")
    st.subheader("📋 Matriz Completa de Ações RFV")

    resumo_acoes = []
    for segmento, info in acoes_marketing.items():
        qtd = len(rfv_segmentado[rfv_segmentado['Segmento'] == segmento])
        resumo_acoes.append({
            'Segmento': segmento,
            'Clientes': qtd,
            'Estratégia': info['Estratégia'],
            'Frequência': info['Frequência'],
            'Canais': info['Canais']
        })

    resumo_df = pd.DataFrame(resumo_acoes)
    st.dataframe(resumo_df, use_container_width=True)

    st.markdown("---")
    st.subheader("📥 Download dos Resultados")

    col1, col2 = st.columns(2)

    with col1:
        csv_rfv = rfv_segmentado.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📊 Download RFV Segmentado (CSV)",
            data=csv_rfv,
            file_name=f'rfv_segmentado_{datetime.now().strftime("%Y%m%d")}.csv',
            mime='text/csv'
        )

    with col2:
        csv_acoes = resumo_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📋 Download Plano de Ações (CSV)",
            data=csv_acoes,
            file_name=f'plano_acoes_rfv_{datetime.now().strftime("%Y%m%d")}.csv',
            mime='text/csv'
        )

# Rodapé
st.markdown("---")
st.markdown("📊 **Dashboard RFV** | Desenvolvido para análise de segmentação de clientes")