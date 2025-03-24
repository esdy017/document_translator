import base64
import os
import time
from dotenv import load_dotenv
import json

import fitz  # PyMuPDF
import streamlit as st
from mistralai import Mistral

# Load environment variables first
load_dotenv()


def display_document_preview(preview_src):
    with st.container():
        st.subheader("Document Preview")
        for page_num, img_src in enumerate(preview_src):
            st.image(img_src, caption=f"Page {page_num + 1}")


def create_download_link(data, filetype, filename):
    b64 = base64.b64encode(data.encode()).decode()
    href = f'<a href="data:{filetype};base64,{b64}" download="{filename}">Download {filename}</a>'
    st.markdown(href, unsafe_allow_html=True)


class DocumentTranslator:
    def __init__(self):
        self.api_key = os.getenv("MISTRAL_API_KEY")
        self.client = Mistral(api_key=self.api_key)
        self.api_model = "mistral-ocr-latest"
        self.file_type = None
        self.target_languages = None
        self.uploaded_files = None

    def initialize_session_state(self):
        if "ocr_results" not in st.session_state:
            st.session_state.ocr_results = []
        if "translation_results" not in st.session_state:
            st.session_state.translation_results = []
        if "preview_src" not in st.session_state:
            st.session_state.preview_src = []
        if "processing_steps" not in st.session_state:
            st.session_state.processing_steps = {}

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

    def ocr_processing(self, client, document):
        try:
            ocr_response = client.ocr.process(
                model=self.api_model,
                document=document,
                include_image_base64=True
            )
            time.sleep(1)

            processed_pages = []
            for page in ocr_response.pages:
                markdown_content = page.markdown
                if hasattr(page, 'images') and page.images:
                    for idx, image in enumerate(page.images):
                        if hasattr(image, 'base64'):
                            base64_image = image.base64
                            markdown_content = markdown_content.replace(
                                f"img-{idx}.jpeg",
                                f"data:image/jpeg;base64,{base64_image}"
                            )
                processed_pages.append(markdown_content)
            return "\n\n".join(processed_pages) or "No result found."
        except Exception as e:
            return f"OCR Error: {str(e)}"

    def display_results(self, file_type):
        for idx, result in enumerate(st.session_state["ocr_results"]):
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Original Preview")
                if idx < len(st.session_state.preview_src):
                    display_document_preview(st.session_state.preview_src[idx])

            with col2:
                st.subheader(f"OCR Results {idx + 1}")
                st.markdown(result, unsafe_allow_html=True)

                st.subheader("Download Options")
                json_data = json.dumps({"ocr_result": result}, ensure_ascii=False, indent=2)
                create_download_link(json_data, "application/json", f"Output_{idx + 1}.json")
                create_download_link(result, "text/plain", f"Output_{idx + 1}.txt")
                create_download_link(result, "text/markdown", f"Output_{idx + 1}.md")

    def main(self):
        self.configure_page()
        self.initialize_session_state()

        if st.button("Process Documents"):
            if not self.uploaded_files:
                st.error("Please upload files first")
                return

            if not self.api_key:
                st.error("Missing Mistral API key in .env file")
                st.stop()

            # Reset previous results
            st.session_state.ocr_results = []
            st.session_state.translation_results = []
            st.session_state.preview_src = []
            st.session_state.processing_steps = {}

            # OCR
            for idx, file in enumerate(self.uploaded_files):
                with st.status(f"Processing {file.name}...", expanded=True):
                    try:
                        # OCR Processing
                        st.write("🔍 Performing OCR...")
                        processed = self.process_pdf(file) if self.file_type == "PDF" else self.process_image(file)
                        ocr_result = self.ocr_processing(self.client, processed["document"])

                        # Store OCR results
                        st.session_state.ocr_results.append(ocr_result)
                        st.session_state.preview_src.append(processed["preview_src"])

                        # Show preview immediately
                        st.write("📄 Document Preview:")
                        display_document_preview(processed["preview_src"])

                        # Store processing state
                        st.session_state.processing_steps[idx] = {
                            "ocr_done": True,
                            "translation_done": False
                        }
                    except Exception as e:
                        st.error(f"OCR failed: {str(e)}")
                        continue

            # Display results if available
            if st.session_state["ocr_results"]:
                self.display_results(self.file_type)


if __name__ == "__main__":
    app = DocumentTranslator()
    app.main()
