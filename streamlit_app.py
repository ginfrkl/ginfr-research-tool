import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import requests
import time
from pathlib import Path
import hmac

THIS_DIR = Path(__file__).parent
ASSETS  = THIS_DIR / 'assets'

ref_df = pd.read_csv(ASSETS / 'Keyword.csv')

def df_grouby_link(raw_df):
    grouped_df = raw_df.groupby('Link')
    new_df = pd.DataFrame(columns=['Category', 'Event', 'Title', 'Link', 'Popularity'])
    links = grouped_df.first().index.tolist()

    for i in range(len(links)):
        group = grouped_df.get_group(links[i])
        event_list = list(set(group['Event'].tolist()))
        cat_list = list(set(group['Category'].tolist()))
        new_df.loc[i] = [' / '.join(cat_list), ' / '.join(event_list), group['Title'].values[0], group['Link'].values[0], len(group)]
    
    new_df.sort_values('Popularity', ascending=False, inplace=True)
    new_df.drop(['Popularity'], axis=1, inplace=True)
    new_df.reset_index(inplace=True)
    return new_df

def get_keyword_combination(df, cat, event):
    # Function to get keyword combination
    # Keyword Combination = Keyword + Common Type
    # v2 
    word_list = []
    event_row = df.loc[(df['Cat_code'] == cat) & (df['Event'] == event)]

    if event_row['Keyword'].isnull().any() == False:
        keyword_list = event_row['Keyword'].item().split('/')
        for i in range(len(keyword_list)):
            keyword_list[i] = keyword_list[i].strip()

        if event_row['Common Type'].isnull().any() == False:
            common_type_list = event_row['Common Type'].item().split('/')
            for i in range(len(common_type_list)):
                common_type_list[i] = common_type_list[i].strip()

            keyword = ' '.join(keyword_list) + ' ' + ' '.join(common_type_list)
            word_list.append(keyword)
        else:
            keyword = ' '.join(keyword_list)
            word_list.append(keyword)
    else:
        pass

    return word_list

def google_query(project, co_name, keyword_list):
    headers = {
    'User-agent':
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }

    result_title_list = []
    result_url_list = []

    if len(keyword_list) != 0:
        for keyword in keyword_list:
            query = project + ' ' + co_name + ' ' + keyword
            html = requests.get(f'https://www.google.com/search?q={query}', headers=headers)
            soup = BeautifulSoup(html.text, 'lxml')

            for result in soup.select('.tF2Cxc')[:5]: #limit the search to top 5 result
                result_title_list.append(result.select('.DKV0Md')[0].text)
                result_url_list.append(result.select('.yuRUbf a')[0]['href'])

        search_result_df = pd.DataFrame({'Title': result_title_list, 'Link': result_url_list})
        search_result_df.drop_duplicates(inplace=True)
        return search_result_df
    else:
        return None

def search_by_cat(project, co_name, cat, df):
    final_result_df = pd.DataFrame()
    if cat < 6:
        for i in range(cat+1):
            for event in df.loc[df['Cat_code'] == i]['Event'].tolist():
                keyword_list = get_keyword_combination(df, i, event)
                temp_df = google_query(project, co_name, keyword_list)
                if temp_df is not None:
                    temp_df['Event'] = [event] * len(temp_df)
                    temp_df['Category'] = [df.loc[df['Cat_code'] == i]['Category'].tolist()[0]] * len(temp_df)

                    final_result_df = pd.concat([final_result_df, temp_df], ignore_index=True, sort=False)
    else:
        for event in df.loc[df['Cat_code'] == 6]['Event'].tolist():
                keyword_list = get_keyword_combination(df, 6, event)
                temp_df = google_query(project, co_name, keyword_list)
                if temp_df is not None:
                    temp_df['Event'] = [event] * len(temp_df)
                    temp_df['Category'] = [df.loc[df['Cat_code'] == 6]['Category'].tolist()[0]] * len(temp_df)

                    final_result_df = pd.concat([final_result_df, temp_df], ignore_index=True, sort=False)

    final_result_df = final_result_df[['Category', 'Event', 'Title', 'Link']]

    new_df = df_grouby_link(final_result_df)
    new_df = new_df.reset_index()
    new_df = new_df[['Category', 'Event', 'Title', 'Link']]

    return new_df

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password.
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False

def main():
     # --- MAIN ---
    st.set_page_config(
    page_title="GINFR Research Tool",
    page_icon="🔎",
    layout="wide")

    # --- SIDEBAR ---
    st.sidebar.write("""
    # GINFR Research Tool
    """)
    st.sidebar.header("Please Search Here:")
    with st.sidebar.form("search_input"):
        project_keyword = st.text_input('**Project** Keyword:')
        company_keyword = st.text_input('**Company** Keyword:')
        stage_list = ['Early Stage', 'Tender Bid', 'Contract Awarded', 'Construct Milestone', 'Finance Related', 'Acquisition/Privitization']
        current_stage = st.selectbox('Current Stage:', tuple(stage_list))
        slcted_cat_code = ref_df.loc[ref_df['Category'] == current_stage]['Cat_code'].values[0]
        
        submitted = st.form_submit_button("Submit")

    if submitted:
        with st.spinner("Please Wait..."):
            start_time = time.time()
            df = search_by_cat(project_keyword, company_keyword, slcted_cat_code, ref_df)
            st.write("Total Results: %s" % (len(df)))
            st.write("--- %s seconds ---"  % (time.time() - start_time))
            st.dataframe(df, column_config={"Link": st.column_config.LinkColumn()}, height=(len(df) + 1) * 35 + 3)


if __name__ == "__main__":
    if not check_password():
        st.stop()  # Do not continue if check_password is not True.
    else:
        main()