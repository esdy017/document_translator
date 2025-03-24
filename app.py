import base64

import streamlit as st
import fitz # PyMuPDF


def display_document_preview(preview_src):
    with st.container():
        st.subheader("Document Preview")
        for page_num, img_src in enumerate(preview_src):
            st.image(img_src, caption=f"Page {page_num + 1}")


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

    def process_pdf(self, source):
        file_bytes = source.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        page_images = []
        for page in doc:
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            base64_image = base64.b64encode(img_bytes).decode("utf-8")
            page_images.append(f"data:image/png;base64,{base64_image}")

        return {
            "document": {
                "type": "document_url",
                "document_url": f"data:application/pdf;base64,{base64.b64encode(file_bytes).decode('utf-8')}"
            },
            "preview_src": page_images,
            "file_bytes": None
        }

    def process_image(self, source):
        # Read uploaded image file
        file_bytes = source.read()

        # Get MIME type from uploaded file
        mime_type = source.type  # e.g. "image/jpeg" or "image/png"

        # Create base64 encoded version for preview
        encoded_image = base64.b64encode(file_bytes).decode("utf-8")

        return {
            "document": {
                "type": "image_url",
                "image_url": f"data:{mime_type};base64,{encoded_image}"
            },
            "preview_src": [f"data:{mime_type};base64,{encoded_image}"],
            "file_bytes": file_bytes
        }

    def main(self):
        self.configure_page()

        for idx, file in enumerate(self.uploaded_files):
            with st.status(f"Processing {file.name}...", expanded=True):
                try:
                    processed = self.process_pdf(file) if self.file_type == "PDF" else self.process_image(file)
                    st.write("📄 Document Preview:")
                    display_document_preview(processed["preview_src"])

                except Exception as e:
                    st.error(f"Can't preview document: {str(e)}")
                    continue


if __name__ == "__main__":
    app = DocumentTranslator()
    app.main()
