import streamlit as st
import requests
import base64
from PIL import Image
import io
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.environ.get("API_URL", "http://localhost:8000")
re_correct_flag = False

st.set_page_config(layout="wide")

# =====================
# SESSION MANAGEMENT
# =====================
if "image" not in st.session_state:
    st.session_state.image = None
if "api_response" not in st.session_state:
    st.session_state.api_response = None
if "selected_corrections" not in st.session_state:
    st.session_state.selected_corrections = None
if "adding_corrections" not in st.session_state:
    st.session_state.adding_corrections = False
if "selecting_corrections" not in st.session_state:
    st.session_state.selecting_corrections = False
if "correction_inputs" not in st.session_state:
    st.session_state.correction_inputs = {"mistake": "", "correction": "", "mistake_type": ""}


# =====================
# FILE UPLOADER
# =====================

st.markdown("<h1 style='text-align: center;'>Ma petite dictée</h1>", unsafe_allow_html=True)

st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)

image = st.file_uploader(
    label="Upload your text image and have your text corrected!",
    type=["heic", "jpg", "jpeg", "png"],
    accept_multiple_files=False
)

if st.button("**Click here and start correcting!**"):
    st.session_state.image = image
    st.session_state.api_response = None
    st.session_state.selected_corrections = None
    st.session_state.adding_corrections = False
    st.session_state.selecting_corrections = False
    st.session_state.correction_inputs = {"mistake": "", "correction": "", "mistake_type": ""}
    re_correct_flag = False
    st.markdown("Your image and text are being processed. Please wait...")

st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.image is not None:

    if st.session_state.api_response is None :
        url = f"{API_URL}/predict"
        files = {"image": image.getvalue()}
        response = requests.post(url, files=files)
        response.raise_for_status()
        st.session_state.api_response = response.json()

    data = st.session_state.api_response

    img_data = base64.b64decode(data["image_base64"])
    image_corrected = Image.open(io.BytesIO(img_data))

    st.markdown("#### **Corrected text**")
    st.markdown(data["json_output"]["corrected_text"])

    st.markdown("#### **Proposed corrected image**")

    col1, col2 = st.columns(2)
    with col1:
        # st.markdown("Scroll down to add or remove corrections.")
        st.image(image_corrected)

# =====================
# ADD CORRECTIONS
# =====================
    with col2:
        if st.button("Click here to add corrections in your image:"):
            st.session_state.adding_corrections = not st.session_state.adding_corrections

        # Show input if correction mode is active
        if st.session_state.adding_corrections:
            mistake = st.text_input("Enter the text to correct:", key="mistake")
            if mistake:
                st.write("You entered:", mistake)
            correction = st.text_input("Enter corrected text:", key="correction")
            if correction:
                st.write("You entered:", correction)
            mistake_type = st.text_input("Enter the type of the mistake (Choose among among the following categories: Spelling, Conjugation, Agreement, Syntax, Article, Punctuation and Lexical)", key="mistake_type")
            if mistake_type:
                st.write("You entered:", mistake_type)
                if mistake_type not in ["Spelling", "Conjugation", "Agreement", "Syntax", "Article", "Punctuation", "Lexical"]:
                    st.markdown("MISTAKE CATEGORY UNKNOWN, PLEASE CHECK!")
            if mistake and correction and mistake_type and st.button("Validate extra corrections!"):
                data["json_output"]["mistakes"].append({
                                        "original": mistake,
                                        "corrected": correction,
                                        "type": mistake_type
                                                    })
                st.markdown("Correction added:")
                st.markdown(f"Original text: {mistake} → Corrected: {correction}  ({mistake_type})")

    # =====================
    # SELECT CORRECTIONS
    # =====================
        if st.button("Click here to select the corrections you want to keep:"):
            st.session_state.selecting_corrections = not st.session_state.selecting_corrections

        if st.session_state.selecting_corrections:
            corrections = data["json_output"]["mistakes"]
            # Ensure we have a place to store selected states
            if st.session_state.selected_corrections is None:
                st.session_state.selected_corrections = [False] * len(corrections)
            else:
            # Resize if number of corrections has changed
                diff = len(corrections) - len(st.session_state.selected_corrections)
                if diff > 0:  # new corrections added
                    st.session_state.selected_corrections.extend([False] * diff)
                elif diff < 0:  # corrections removed
                    st.session_state.selected_corrections = st.session_state.selected_corrections[:len(corrections)]

            select_all = st.checkbox("**Select / Deselect All Corrections**", key="select_all_checkbox")
            if select_all:
                st.session_state.selected_corrections = [True] * len(corrections)
            elif not select_all and all(st.session_state.selected_corrections):
                # If previously all were selected and user unchecks, deselect all
                st.session_state.selected_corrections = [False] * len(corrections)

            for i, correction in enumerate(corrections):
                # Persist checkbox state with session_state
                st.session_state.selected_corrections[i] = st.checkbox(
                    f"Original text: {correction['original']} → Corrected: {correction['corrected']}  ({correction['type']})",
                    key=f"correction_{i}",
                    value=st.session_state.selected_corrections[i]
                )

            # Build the selected list based on checkboxes
            selected = [
                corr for corr, keep in zip(corrections, st.session_state.selected_corrections) if keep
            ]

            if st.button("Click here to validate the corrections you want to see in your image."):
                data["json_output"]["mistakes"] = selected

                st.markdown("✅ **Corrections selected:**")
                for i, mistake in enumerate(selected):
                    st.markdown(f"Original text: {mistake['original']} → Corrected: {mistake['corrected']}  ({mistake['type']})")

        if st.button("**Re-correct the text of your image!**"):
            re_correct_flag = True

    col3, col4 = st.columns(2)
    with col3:
        if re_correct_flag:

            url_repredict = f"{API_URL}/re_predict"

            payload = {
                "json_output": data["json_output"],           # updated mistakes
                "image_proc_base64": data["image_proc_base64"] # original processed image
                    }

            response = requests.post(url_repredict,json=payload)
            response.raise_for_status()
            data_final = response.json()

            img_data = base64.b64decode(data_final["image_base64"])
            image_corrected_bis = Image.open(io.BytesIO(img_data))

            # Convert to PDF in memory
            buf = io.BytesIO()
            image_corrected_bis.save(buf, format="PDF")  # PIL requires RGB for PDF
            pdf_bytes = buf.getvalue()

            st.markdown("#### **Your custom corrected image**")

            st.image(image_corrected_bis)

    with col4:
    # Convert to PDF in memory
        if re_correct_flag:
            buf = io.BytesIO()
            image_corrected_bis.save(buf, format="PDF")  # PIL requires RGB for PDF
            pdf_bytes = buf.getvalue()
        else :
            buf = io.BytesIO()
            image_corrected.save(buf, format="PDF")  # PIL requires RGB for PDF
            pdf_bytes = buf.getvalue()

        # Download button
        st.download_button(
            label="**Click here to download your corrected image as PDF!**",
            data=pdf_bytes,
            file_name="result.pdf",
            mime="application/pdf"
            )
