import streamlit as st


class DocumentTranslator:
    def __init__(self):
        self.file_type = None
        self.target_languages = None
        self.uploaded_files = None

    def configure_page(self):
        st.set_page_config(layout="wide", page_title="Document Translator")
        st.title("Translate Your Document")

        self.file_type = st.radio("Document Type", ["PDF", "Image"])
        self.target_languages = st.selectbox("Select a Target Language", [
            "French", "Spanish", "German", "Italian",
            "Chinese", "Japanese", "Korean", "Russian",
            "English"
        ])
        self.uploaded_files = st.file_uploader(
            "Upload Files",
            type=["pdf", "jpg", "jpeg", "png"],
            accept_multiple_files=True
        )
        if st.button("Process Documents"):
            if not self.uploaded_files:
                st.error("Please upload files first")
                return

    def main(self):
        self.configure_page()


if __name__ == "__main__":
    app = DocumentTranslator()
    app.main()
