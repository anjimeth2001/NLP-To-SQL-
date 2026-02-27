import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


# ===============================
# Database Connection
# ===============================
def get_engine(database=None):

    username = "root"
    password = "password"
    host = "localhost"

    if database:
        return create_engine(
            f"mysql+pymysql://{username}:{password}@{host}/{database}"
        )

    return create_engine(
        f"mysql+pymysql://{username}:{password}@{host}"
    )


# ===============================
# Metadata Functions
# ===============================
def get_databases():
    engine = get_engine()
    df = pd.read_sql("SHOW DATABASES", engine)
    return df["Database"].tolist()


def get_tables(database):
    engine = get_engine(database)
    df = pd.read_sql("SHOW TABLES", engine)
    return df.iloc[:,0].tolist()


# ===============================
# AI SQL Generator
# ===============================
def get_sql_query(user_query, table_name):

    prompt = ChatPromptTemplate.from_template("""
    You are SQL expert.

    Table Name:
    {table_name}

    Convert question to MySQL query.

    Rules:
    - Return only SQL query
    - No ``` or explanation

    Question:
    {user_query}
    """)

    llm = ChatGroq(
        api_key="GROQ_API_KEY",
        model_name="llama-3.1-8b-instant"
    )

    chain = prompt | llm | StrOutputParser()

    return chain.invoke({
        "user_query": user_query,
        "table_name": table_name
    })


# ===============================
# Update Database
# ===============================
def update_database(engine, table_name, df):

    try:
        df.to_sql(
            table_name,
            engine,
            if_exists="replace",
            index=False
        )
        return True

    except Exception as e:
        st.sidebar.error(e)
        return False


# ===============================
# MAIN APP
# ===============================
def main():

    st.set_page_config(layout="wide")

    st.title("🤖 AI Powered Database Assistant")

    # ================= SESSION STATE INIT =================
    if "show_table" not in st.session_state:
        st.session_state.show_table = False

    # ================= SIDEBAR =================
    st.sidebar.header("Database Explorer")

    databases = get_databases()
    selected_db = st.sidebar.selectbox("Select Database", databases)

    tables = get_tables(selected_db)
    selected_table = st.sidebar.selectbox("Select Table", tables)

    # Editing Tools
    st.sidebar.subheader("✏ Table Editing Tools")

    edit_action = st.sidebar.selectbox(
        "Select Action",
        ["None","Drop Row","Drop Column Index",
         "Drop Column Name","Rename Column"],
        key="edit_action_select"
    )

    edit_value = st.sidebar.text_input(
        "Enter Value",
        key="edit_value_input"
    )

    # ================= LOAD DATA =================
    engine = get_engine(selected_db)

    df = pd.read_sql(
        f"SELECT * FROM {selected_table}",
        engine
    )

    # Apply Edit
    if edit_action != "None" and edit_value:

        try:
            if edit_action == "Drop Row":
                df = df.drop(index=int(edit_value))

            elif edit_action == "Drop Column Index":
                df = df.drop(df.columns[int(edit_value)], axis=1)

            elif edit_action == "Drop Column Name":
                df = df.drop(edit_value, axis=1)

            elif edit_action == "Rename Column":
                old,new = edit_value.split(",")
                df = df.rename(columns={old.strip():new.strip()})

        except Exception as e:
            st.sidebar.error(e)

    # ================= UPDATE TABLE =================
    if st.sidebar.button("✅ Update Table In Database"):

        if update_database(engine, selected_table, df):

            st.sidebar.success("Database Updated Successfully!")

            st.rerun()

    # ================= TABLE PREVIEW (HIDDEN BAR) =================
    with st.expander("📊 View Table Preview", expanded=False):
        st.dataframe(df, use_container_width=True)

    st.divider()

    # ================= QUERY SECTION =================
    col_left, col_right = st.columns(2)

    with col_left:

        st.subheader("💬 AI Query Assistant")

        user_query = st.text_area("Ask Database Question", height=120)

        if st.button("Run Query"):

            sql_query = get_sql_query(
                user_query,
                selected_table
            )

            with st.expander("🔎 Generated SQL Query"):
                st.code(sql_query)

            try:
                result = pd.read_sql(sql_query, engine)

                with col_right:
                    st.subheader("📈 Query Results")
                    st.dataframe(result, use_container_width=True)

            except Exception as e:
                st.error(e)


# ===============================
if __name__ == "__main__":
    main()
