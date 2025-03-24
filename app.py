import streamlit as st


def configure_page():
    st.set_page_config(layout="wide", page_title="Document Translator")
    st.title("Translate Your Document")


def main():
    configure_page()


if __name__ == "__main__":
    main()
