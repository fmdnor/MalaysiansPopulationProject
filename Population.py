import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def age_catergory(df_pop_age: pd.DataFrame):
    age_cat = {
        '1. kanak-kanak': ['0-4', '5-9'],
        '2. remaja': ['10-14', '15-19'],
        '3. dewasa_muda': ['20-24', '25-29', '30-34', '35-39'],
        '4. dewasa_pertengahan': ['40-44', '45-49', '50-54', '55-59'],
        '5. wargaemas': ['60-64', '65-69', '70-74', '75-79', '80-84', '85+', '70+']
    }

    age_map = {}
    for category, ages in age_cat.items():
        for age in ages:
            age_map[age] = category
    df_pop_age['age_category'] = df_pop_age['age'].map(age_map)

    df_filtered = df_pop_age.dropna(subset=['age_category'])
    df_result = (
        df_filtered
        .groupby(['date','age_category'])['population']
        .sum()
        .reset_index()
    )
    df_pivot_results = (
        df_result
        .pivot_table(index='date', columns='age_category', values='population', aggfunc='sum')
        .fillna(0)
    )
    df_pivot_results['total'] = df_pivot_results.sum(axis=1)
    df_pivot_results.reset_index(inplace=True)
    return df_pivot_results

def get_population():
    url_population = 'https://storage.dosm.gov.my/population/population_malaysia.parquet'
    df_pop = pd.read_parquet(url_population)
    if 'date' in df_pop.columns:
        df_pop['date'] = pd.to_datetime(df_pop['date'])
    return df_pop

def population_by_year(df_population: pd.DataFrame):
    df_population_all = df_population[
        (df_population['sex'] == 'both') & (df_population['ethnicity'] == 'overall') & (
                    df_population['age'] == 'overall')
        ].copy()
    df_population_all['date'] = pd.to_datetime(df_population_all['date'], format='%Y').dt.strftime('%Y')
    df_Mal_pop_by_year = df_population_all[['date', 'population']].copy().reset_index(drop=True)

    return df_Mal_pop_by_year

def population_by_gender(df_population: pd.DataFrame):
    df_gender = df_population[
        (df_population['sex'] != 'both') & (df_population['ethnicity'] == 'overall') & (
                    df_population['age'] == 'overall')
        ].copy()

    df_gender = df_gender[['date', 'sex', 'population']].copy()
    df_gender['date'] = pd.to_datetime(df_gender['date'], format='%Y').dt.strftime('%Y')
    df_gender.reset_index(drop=True, inplace=True)

    df_male = df_gender[df_gender['sex'] == 'male']
    df_male = df_male[['date', 'population']].copy()
    df_male.rename(columns={'population': 'male'}, inplace=True)

    df_female = df_gender[df_gender['sex'] == 'female']
    df_female = df_female[['date', 'population']].copy()
    df_female.rename(columns={'population': 'female'}, inplace=True)
    return df_male, df_female

def population_by_ages(df_population: pd.DataFrame):
    df = df_population[
        (df_population['sex'] == 'both') & (df_population['age'] != 'overall') & (
                df_population['ethnicity'] == 'overall')].copy()
    df_pop_by_ages = df[['date', 'age', 'population']].copy()
    df_pop_by_ages['date'] = pd.to_datetime(df_pop_by_ages['date'], format='%Y').dt.strftime('%Y')

    population_age_cat = age_catergory(df_pop_by_ages)

    df_ages = (
        df_pop_by_ages
        .pivot_table(index='date', columns='age', values='population', aggfunc='sum')
        .fillna(0)
    )

    df_ages['total'] = df_ages.sum(axis=1)
    df_ages = df_ages.reset_index()
    return df_ages, population_age_cat

df_population = get_population()
df_population['population'] = df_population['population'].astype(int) * 1000
df_Mal_pop = population_by_year(df_population=df_population)
df_male_pop, df_female_pop = population_by_gender(df_population=df_population)
df_by_ages, df_age_category = population_by_ages(df_population=df_population)
df_pop_by_gender = pd.merge(df_female_pop, df_male_pop, on='date', how='left')
df_pop_by_gender['total'] = df_pop_by_gender['male'] + df_pop_by_gender['female']

fig = px.line(
    df_Mal_pop,
    x='date',
    y='population',
    title='Populasi Malaysia (Tahun)',
    labels={
        'date': 'Tahun',
        'population': 'Jumlah Populasi'
    }
)

fig.update_traces(
    hovertemplate='Tahun: %{x}<br>Populasi: %{y:,.0f}<extra></extra>'
)

fig.update_layout(yaxis=dict(tickformat='.2s'))

fig.show()

fig1 = px.line(
    df_pop_by_gender,
    x='date',
    y=['male', 'female', 'total'],
    title='Populasi Malaysia Mengikut Jantina',
    labels={
        'date': 'Tahun',
        'value': 'Populasi',
        'variable': 'Kategori'
    }
)

fig1.for_each_trace(lambda t: t.update(name={
    'male': 'Lelaki',
    'female': 'Perempuan',
    'total': 'Jumlah'
}[t.name]))

fig1.update_traces(
    hovertemplate='Tahun: %{x}<br>Populasi: %{y:,.0f}<extra></extra>'
)

fig1.update_layout(yaxis=dict(tickformat='.2s'))

fig1.show()

fig_age_category = px.bar(
    df_age_category,
    x='date',
    y=df_age_category.columns[1:-1],
    title='Populasi Mengikut Kategori Umur',
    labels={
        'date': 'Tahun',
        'value': 'Populasi',
        'variable': 'Kumpulan Umur'
    }
)

fig_age_category.update_layout(
    barmode='stack',
    yaxis=dict(tickformat='.2s')
)
fig_age_category.show()

fig2 = px.bar(
    df_by_ages,
    x='date',
    y=df_by_ages.columns[1:-1],
    title='Populasi Mengikut Peringkat Umur',
    labels={
        'date': 'Tahun',
        'value': 'Populasi',
        'variable': 'Kumpulan Umur'
    }
)

fig2.update_layout(
    barmode='stack',
    yaxis=dict(tickformat='.2s')
)

fig2.show()

fig3 = go.Figure()

fig3.add_bar(
    x=df_pop_by_gender['date'],
    y=df_pop_by_gender['male'],
    name='Lelaki'
)

fig3.add_bar(
    x=df_pop_by_gender['date'],
    y=df_pop_by_gender['female'],
    name='Perempuan'
)

fig3.add_scatter(
    x=df_pop_by_gender['date'],
    y=df_pop_by_gender['total'],
    name='Jumlah',
    mode='lines+markers',
    line=dict(color='black', width=3)
)

fig3.update_layout(
    title='Populasi Malaysia Mengikut Jantina',
    xaxis_title='Tahun',
    yaxis_title='Populasi',
    barmode='stack',
    yaxis=dict(tickformat='.2s'),
    legend_title='Kategori'
)

fig3.show()