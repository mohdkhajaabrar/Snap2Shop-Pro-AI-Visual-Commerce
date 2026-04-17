import streamlit as st
from PIL import Image
import io
import urllib.parse
import time
import requests
import json
import base64
import streamlit as st
import google.generativeai as genai

if "api_key" not in st.session_state:
    st.session_state.api_key = ""
# Set Page Config
st.set_page_config(
    page_title='Snap2Shop Pro | AI Visual Commerce',
    page_icon='🛍️',
    layout='wide',
    initial_sidebar_state='expanded'
)


# --- CONFIG & API SETUP ---
api_key = st.session_state.get("api_key", "")
def call_gemini_vision(image_bytes, prompt):
    """Calls Gemini 2.5 Flash for Visual Analysis with Multi-Object Support"""
    model_id = "gemini-2.5-flash"
    api_key = st.session_state.get("api_key", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
    
    encoded_image = base64.b64encode(image_bytes).decode('utf-8')
    
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inlineData": {"mimeType": "image/jpeg", "data": encoded_image}}
            ]
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "detected_objects": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "item_name": {"type": "STRING"},
                                "style": {"type": "STRING"},
                                "keywords": {"type": "ARRAY", "items": {"type": "STRING"}},
                                "advice": {"type": "STRING"}
                            },
                            "required": ["item_name", "style", "keywords", "advice"]
                        }
                    }
                },
                "required": ["detected_objects"]
            }
        }
    }
    
    last_error = ""
    for delay in [1, 2, 4]:
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                last_error = f"Error {response.status_code}: {response.text}"
                if response.status_code == 404:
                    break
        except Exception as e:
            last_error = str(e)
            time.sleep(delay)
            
    return {"error": last_error}


# --- UI COMPONENTS ---

st.sidebar.title("🛠️ Control Center")
mode = st.sidebar.selectbox("Input Mode", ["Upload Image", "Real-time Camera"])
st.sidebar.divider()
st.sidebar.info("""
**Upgrades included:**
- Multi-Object Detection Logic
- Stable Gemini 2.5 Flash Migration
- Style-aware Search Keywords
- AI Buying Consultant
""")

api_key_input = st.text_input(
        "API Key",
        type="password",
        value=st.session_state.api_key,
        
    )

    # Button
if st.button("Set API Key"):
    if api_key_input:
        st.session_state.api_key = api_key_input
        genai.configure(api_key=st.session_state.api_key)
        st.success("API key set successfully ✓")
    else:
        st.error("Please enter API key")
st.markdown("""
<style>
div[data-testid="stSidebar"] {
    background-color: #1e1e1e;
}
</style>
""", unsafe_allow_html=True)
st.title("🛍️ Snap2Shop Pro")
st.markdown("### *Multi-Product AI Visual Search*")

def get_shopping_links(query):
    q = urllib.parse.quote(query)
    return {
        "Google Shopping": f"https://www.google.com/search?tbm=shop&q={q}",
        "Amazon": f"https://www.amazon.in/s?k={q}",
        "Myntra/Flipkart": f"https://www.flipkart.com/search?q={q}"
    }

img_input = None
if mode == "Upload Image":
    up = st.file_uploader("Drop a photo with multiple products", type=['png', 'jpg', 'jpeg'])
    if up:
        img_input = up.getvalue()
else:
    cam = st.camera_input("Snap a photo of a scene")
    if cam:
        img_input = cam.getvalue()

if img_input:
    image = Image.open(io.BytesIO(img_input))
    
    col1, col2 = st.columns([1, 1.2])
    
    with col1:
        st.image(image, caption="Source Image", use_container_width=True)
        analyze_btn = st.button("🔍 Snap & Shop All Items", type="primary", use_container_width=True)

    if analyze_btn:
        with col2:
            with st.status("🚀 Deep Scanning Scene...", expanded=True) as status:
                st.write("Detecting all purchasable items...")
                
                prompt = """
                Identify ALL distinct purchasable products in this image (e.g., chair, table, lamp, laptop). 
                For each item: 
                1. Name it specifically.
                2. Describe its style/aesthetic.
                3. Provide 3 specific search keywords.
                4. Give one pro-tip for buying this item.
                Return the list as a JSON array named 'detected_objects'.
                """
                
                result = call_gemini_vision(img_input, prompt)
                
                if result and "error" not in result:
                    status.update(label=f"Found {len(json.loads(result['candidates'][0]['content']['parts'][0]['text'])['detected_objects'])} items!", state="complete", expanded=False)
                    
                    try:
                        content = result['candidates'][0]['content']['parts'][0]['text']
                        data = json.loads(content)
                        
                        for idx, item in enumerate(data['detected_objects']):
                            with st.container(border=True):
                                st.markdown(f"#### {idx+1}. {item['item_name']}")
                                st.caption(f"**Style:** {item['style']}")
                                
                                # Links row
                                main_query = item['keywords'][0] if item['keywords'] else item['item_name']
                                links = get_shopping_links(main_query)
                                l_cols = st.columns(3)
                                for i, (name, url) in enumerate(links.items()):
                                    l_cols[i].link_button(name, url, use_container_width=True)
                                
                                # Advice and Keywords in an expander to save space
                                with st.expander("Details & Refined Search"):
                                    st.write(f"💡 **Buying Tip:** {item['advice']}")
                                    st.write("**Alternative Keywords:**")
                                    st.write(", ".join(item['keywords']))

                    except Exception as e:
                        st.error(f"Analysis failed: {str(e)}")
                else:
                    status.update(label="Service Error", state="error")
                    st.error(result.get("error", "AI Service unavailable"))

# Footer
st.markdown("---")
st.caption("Snap2Shop Pro v3.0 | Multi-Object Detection | Powered by Google Gemini")
