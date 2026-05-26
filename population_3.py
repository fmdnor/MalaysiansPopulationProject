import pandas as pd
import plotly.express as px
import streamlit as st

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet

from openai import OpenAI
import tempfile
from datetime import datetime

# ✅ Initialize AI client
client = OpenAI(api_key="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")


# ======================
# DATA LOADING
# ======================
@st.cache_data
def get_population():
    url = 'https://storage.dosm.gov.my/population/population_malaysia.parquet'
    df = pd.read_parquet(url)

    df['date'] = pd.to_datetime(df['date']).dt.year.astype(str)
    df['population'] = df['population'].astype(int) * 1000

    return df


# ======================
# DATA TRANSFORMATION
# ======================
def population_by_year(df):
    return df[
        (df['sex'] == 'both') &
        (df['ethnicity'] == 'overall') &
        (df['age'] == 'overall')
    ][['date', 'population']].sort_values('date')


def population_by_gender(df):
    df_gender = df[
        (df['sex'] != 'both') &
        (df['ethnicity'] == 'overall') &
        (df['age'] == 'overall')
    ]

    male = df_gender[df_gender['sex'] == 'male'][['date', 'population']].rename(columns={'population': 'male'})
    female = df_gender[df_gender['sex'] == 'female'][['date', 'population']].rename(columns={'population': 'female'})

    df_merge = pd.merge(male, female, on='date')
    df_merge['total'] = df_merge['male'] + df_merge['female']

    return df_merge.sort_values('date')


def age_category(df):
    age_cat = {
        'Kanak-kanak': ['0-4', '5-9'],
        'Remaja': ['10-14', '15-19'],
        'Dewasa Muda': ['20-24', '25-29', '30-34', '35-39'],
        'Dewasa Pertengahan': ['40-44', '45-49', '50-54', '55-59'],
        'Warga Emas': ['60-64', '65-69', '70-74', '75-79', '80-84', '85+']
    }

    age_map = {age: cat for cat, ages in age_cat.items() for age in ages}
    df['age_category'] = df['age'].map(age_map)

    df = df.dropna(subset=['age_category'])

    df_cat = df.groupby(['date', 'age_category'])['population'].sum().reset_index()

    df_pivot = df_cat.pivot(index='date', columns='age_category', values='population').fillna(0)
    df_pivot['total'] = df_pivot.sum(axis=1)

    return df_pivot.reset_index()


def population_by_ages(df):
    df_age = df[
        (df['sex'] == 'both') &
        (df['ethnicity'] == 'overall') &
        (df['age'] != 'overall')
    ][['date', 'age', 'population']]

    return age_category(df_age)


# ======================
# AI ANALYSIS
# ======================
@st.cache_data
def generate_ai_analysis(df_year, df_gender):
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": str(df_year.iloc[-1])}],
        )

        return response.choices[0].message.content

    except Exception:
        # ✅ fallback insight (no API needed)
        latest = df_year.iloc[-1]['population']
        prev = df_year.iloc[-2]['population']
        growth = ((latest - prev) / prev) * 100

        return f"""
        Malaysia population reached {latest:,.0f}.
        Growth rate is {growth:.2f}% indicating steady increase.
        Overall trend shows long-term population expansion.
        """

# ======================
# CHARTS (COLOR FIXED ✅)
# ======================
def create_charts(df_year, df_gender, df_age_cat):

    fig1 = px.line(df_year, x='date', y='population',
                   title='Jumlah Populasi Malaysia')
    fig1.update_traces(mode='lines+markers')
    fig1.update_layout(template="plotly_white")

    fig2 = px.line(
        df_gender,
        x='date',
        y=['male', 'female', 'total'],
        title='Populasi Mengikut Jantina',
        color_discrete_map={
            'male': '#1f77b4',
            'female': '#e377c2',
            'total': '#000000'
        }
    )
    fig2.update_layout(template="plotly_white")

    fig3 = px.bar(
        df_age_cat,
        x='date',
        y=df_age_cat.columns[1:-1],
        title='Populasi Mengikut Kategori Umur',
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig3.update_layout(barmode='stack', template="plotly_white")

    return fig1, fig2, fig3


# ======================
# PDF GENERATION
# ======================
def generate_pdf(figs, ai_text):

    temp_files = []

    for fig in figs:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")

        fig.write_image(
            tmp.name,
            format="png",
            width=1200,
            height=700,
            scale=2   # ✅ keeps colors
        )

        temp_files.append(tmp.name)

    pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")

    doc = SimpleDocTemplate(pdf.name, pagesize=letter)
    styles = getSampleStyleSheet()

    content = []

    content.append(Paragraph("Laporan Populasi Malaysia", styles['Title']))
    content.append(Spacer(1, 12))

    content.append(Paragraph("AI Analysis", styles['Heading2']))
    content.append(Paragraph(ai_text, styles['Normal']))
    content.append(Spacer(1, 20))

    for path in temp_files:
        content.append(Image(path, width=500, height=300))
        content.append(Spacer(1, 20))

    doc.build(content)

    filename = f"population_report_{datetime.today().strftime('%Y%m%d')}.pdf"

    return pdf.name, filename


# ======================
# STREAMLIT UI
# ======================
st.set_page_config(layout="wide")
st.title("📊 Malaysia Population Dashboard + AI")

df = get_population()

df_year = population_by_year(df)
df_gender = population_by_gender(df)
df_age_cat = population_by_ages(df)

fig1, fig2, fig3 = create_charts(df_year, df_gender, df_age_cat)


# Layout
col1, col2 = st.columns(2)
col1.plotly_chart(fig1, use_container_width=True)
col2.plotly_chart(fig2, use_container_width=True)

st.plotly_chart(fig3, use_container_width=True)


# ======================
# KPI
# ======================
latest = df_year.iloc[-1]['population']
prev = df_year.iloc[-2]['population']
growth = ((latest - prev) / prev) * 100

col1, col2, col3 = st.columns(3)
col1.metric("Population", f"{latest:,.0f}")
col2.metric("Growth %", f"{growth:.2f}%")
col3.metric("Years", len(df_year))


# ======================
# AI INSIGHT
# ======================
st.subheader("🤖 AI Analysis")

with st.spinner("Generating AI insight..."):
    ai_text = generate_ai_analysis(df_year, df_gender)

st.write(ai_text)


# ======================
# PDF EXPORT
# ======================
st.subheader("📄 Export Report")

if st.button("Generate PDF Report"):
    with st.spinner("Generating PDF..."):
        pdf_path, filename = generate_pdf([fig1, fig2, fig3], ai_text)

    with open(pdf_path, "rb") as f:
        st.download_button(
            label="Download PDF",
            data=f,
            file_name=filename,
            mime="application/pdf"
        )
