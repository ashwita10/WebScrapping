import streamlit as st
from backend.pinecone_utils import initialize_pinecone, fetch_all_from_pinecone, store_in_pinecone
from backend.data_scraper import scrape_website
from backend.chatbot_logic import generate_response
from frontend.upload_processing import process_uploaded_files
from backend.embeddings import generate_embeddings
from langchain.llms import Cohere as LangCohere
from langchain.chains import ConversationChain
from langchain.chains.conversation.memory import ConversationSummaryMemory
from streamlit_chat import message

# Streamlit UI Configuration
st.set_page_config(page_title="Chatbot", page_icon=":robot_face:")
st.title("Chatbot 🤖")

# Initialize Pinecone and other configurations
pinecone_index = initialize_pinecone()

# Sidebar for Data Upload & Web Scraping
st.sidebar.header("Data Input")
uploaded_files = st.sidebar.file_uploader("Upload Files (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"], accept_multiple_files=True)
scrape_button = st.sidebar.button("Scrape Data from VKAPS")

# Scraping Functionality
if scrape_button:
    scraped_content = scrape_website("https://vkaps.com/")
    if scraped_content:
        store_in_pinecone(scraped_content, "vkaps_scraped_data", pinecone_index)
        st.sidebar.success("Data from VKAPS website scraped and stored successfully!")
    else:
        st.sidebar.error("Failed to scrape data from VKAPS.")

# File Upload Handling
if uploaded_files:
    content = process_uploaded_files(uploaded_files)
    for file in uploaded_files:
        store_in_pinecone(content, file.name, pinecone_index)
    st.sidebar.success("Uploaded files processed and stored successfully!")

# Initialize the conversation state
if 'conversation' not in st.session_state:
    st.session_state['conversation'] = None
if 'messages' not in st.session_state:
    st.session_state['messages'] = []

# Function to handle chatbot responses
def getresponse(user_input):
    # Check if the conversation is initialized in session state and is not a list
    if isinstance(st.session_state['conversation'], list):
        st.session_state['conversation'] = None  # Reset if it's mistakenly set as a list

    if st.session_state['conversation'] is None:
        # Initialize the conversation chain with an LLM and memory
        llm = LangCohere(temperature=0, model="command-xlarge-nightly")
        st.session_state['conversation'] = ConversationChain(
            llm=llm,
            verbose=True,
            memory=ConversationSummaryMemory(llm=llm)
        )

    # Add context from Pinecone (if available)
    context = fetch_all_from_pinecone(pinecone_index, generate_embeddings(user_input))
    if context:
        user_input = f"Context: {context}\nQuestion: {user_input}"

    # Ensure we're calling the predict method on the ConversationChain object
    response = st.session_state['conversation'].predict(input=user_input)
    return response


# Chat UI
response_container = st.container()
container = st.container()

with container:
    with st.form(key='my_form', clear_on_submit=True):
        user_input = st.text_area("Your question goes here:", key='input', height=100)
        submit_button = st.form_submit_button(label='Send')

        if submit_button:
            st.session_state['messages'].append(user_input)
            model_response = getresponse(user_input)
            st.session_state['messages'].append(model_response)

            with response_container:
                for i in range(len(st.session_state['messages'])):
                    if (i % 2) == 0:
                        message(st.session_state['messages'][i], is_user=True, key=str(i) + '_user')
                    else:
                        message(st.session_state['messages'][i], key=str(i) + '_AI')