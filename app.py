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
        self.ocr_model = "mistral-ocr-latest"
        self.chat_model = "mistral-large-latest"
        self.file_type = None
        self.target_language = None
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
        self.target_language = st.selectbox("Select a Target Language", [
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
                model=self.ocr_model,
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

    def translate_content(self, client, text, target_language):
        try:
            response = client.chat.complete(
                model=self.chat_model,
                messages=[{
                    "role": "user",
                    "content": f"Translate to {target_language} preserving formatting and images:\n\n{text}"
                }]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Translation Error: {str(e)}"

    def display_results(self, target_language):
        for idx, translated in enumerate(st.session_state.translation_results):
            with st.expander(f"Document {idx + 1} - Full Translation", expanded=True):
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("Original Preview")
                    if idx < len(st.session_state.preview_src):
                        display_document_preview(st.session_state.preview_src[idx])

                with col2:
                    st.subheader(f"Translated Content ({target_language})")
                    st.markdown(translated, unsafe_allow_html=True)

                    st.subheader("Download Options")
                    json_data = json.dumps({"ocr_result": translated}, ensure_ascii=False, indent=2)
                    st.download_button(
                        label="Download Markdown",
                        data=translated,
                        file_name=f"translated_{idx + 1}.md",
                        mime="text/markdown"
                    )
                    st.download_button(
                        label="Download JSON",
                        data=json_data,
                        file_name=f"translated_{idx + 1}.json",
                        mime="application/json"
                    )
                    st.download_button(
                        label="Download Text",
                        data=translated,
                        file_name=f"translated_{idx + 1}.txt",
                        mime="text/plain"
                    )

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
                        # st.write("📄 Document Preview:")
                        # display_document_preview(processed["preview_src"])

                        # Store processing state
                        st.session_state.processing_steps[idx] = {
                            "ocr_done": True,
                            "translation_done": False
                        }
                    except Exception as e:
                        st.error(f"OCR failed: {str(e)}")
                        continue

            # Translation
            for idx, file in enumerate(self.uploaded_files):
                if idx >= len(st.session_state.ocr_results):
                    continue

                with st.status(f"Translating {file.name}...", expanded=True):
                    try:
                        # Get OCR result
                        ocr_text = st.session_state.ocr_results[idx]

                        # Show preview again
                        st.write("📄 Original Content Preview:")
                        st.markdown(ocr_text[:500] + "...", unsafe_allow_html=True)

                        # Perform translation
                        st.write(f"🌍 Translating to {self.target_language}...")
                        translated = self.translate_content(self.client, ocr_text, self.target_language)
                        st.session_state.translation_results.append(translated)

                        # Show translation preview
                        st.write("✅ Translation Complete:")
                        st.markdown(translated[:500] + "...", unsafe_allow_html=True)

                        # Update processing state
                        st.session_state.processing_steps[idx]["translation_done"] = True

                    except Exception as e:
                        st.error(f"Translation failed: {str(e)}")

        # Display results if available
        if st.session_state.translation_results:
            st.divider()
            st.header("Final Results")
            self.display_results(self.target_language)


if __name__ == "__main__":
    app = DocumentTranslator()
    app.main()
