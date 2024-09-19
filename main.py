import openai
import streamlit as st
from qa_utils import load_qa_data, find_best_match, generate_longer_response, extract_text_from_pdf, suggest_related_questions
from email_generation import email_generation_ui  # Ensure this is added
from fuzzywuzzy import fuzz
import random

# Set the OpenAI API key directly (replace with your own)
openai.api_key = "your-openai-api-key"

# Load all questions from multiple JSON files
qa_data = load_qa_data()

# Extract text from the PDF (update to the correct location)
pdf_path = "data/health_cheat.pdf"  # Ensure the PDF is in the 'data/' folder
pdf_text = extract_text_from_pdf(pdf_path)

# Resources for each category (PDF or other links)
resources = {
    "EXL Health Overview": [
        {"label": "EXL Health Overview PDF", "link": "path/to/EXL-Health-Overview.pdf"},  # Replace with actual link
        {"label": "Case Study 1", "link": "path/to/case-study-1.pdf"}
    ],
    "Clinical Services": [
        {"label": "Clinical Services Overview", "link": "path/to/clinical-services-overview.pdf"},
        {"label": "Clinical Services Case Study", "link": "path/to/clinical-case-study.pdf"}
    ],
    # Add more resources for other categories
}

# Helper function to suggest random questions from loaded data
def get_random_questions(category, num=3):
    """ Return random questions from the category. """
    if category in qa_data:
        return random.sample(qa_data[category], min(len(qa_data[category]), num))
    return []

# Helper function to simulate a conversational experience
def conversational_intro():
    st.markdown("""
        ### Hello! I'm your EXL Health Assistant 🤖
        I can help you with information about EXL Health services. Feel free to ask me questions like:
        - "What services does EXL offer?"
        - "Tell me about clinical services"
        - "How can EXL help improve healthcare outcomes?"
    """)

# Function to generate an email using OpenAI (optional)
def generate_email_with_openai(persona, recipient_name, company_name, key_area, pain_points, solution, outcome, cta):
    try:
        # Prepare the context for OpenAI with the custom parameters
        email_context = f"""
        Persona: {persona}
        Recipient: {recipient_name}
        Company: {company_name}
        Key Area: {key_area}
        Pain Points: {pain_points}
        Solution: {solution}
        Outcome: {outcome}
        Call to Action: {cta}
        Context from PDF: {pdf_text}
        """

        # Use OpenAI's ChatCompletion to generate an email based on the context
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Use GPT-4 if available
            messages=[
                {"role": "system", "content": "You are an email writing assistant."},
                {"role": "user", "content": f"Write an email for the following context: {email_context}"}
            ]
        )
        email_content = response['choices'][0]['message']['content']
        return email_content
    except Exception as e:
        st.error(f"Error generating email with OpenAI: {e}")
        return None

# Streamlit UI Enhancements
st.markdown("<h1 style='text-align: center; color: #2E86C1;'>🚀 EXL Health Sales Assistant</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align: center; color: #555;'>Optimize your sales process with AI-driven insights</h4>", unsafe_allow_html=True)

# Tabs for Q&A and Email Generation
tab1, tab2 = st.tabs(["📋 Q&A", "✉️ Email Generation"])

# Default selected category
default_category = "EXL Health Overview"

# Q&A Tab with Conversational Flow
with tab1:
    if qa_data:
        st.subheader("🔍 Let's Start with Some Questions!")

        # Conversational introduction
        conversational_intro()

        # Create two columns for layout
        col1, col2 = st.columns([2, 1])

        # Select a service category for Q&A, defaulting to "EXL Health Overview"
        with col1:
            category = st.selectbox(
                "Which area would you like to know more about?",
                list(qa_data.keys()), 
                index=list(qa_data.keys()).index(default_category), 
                help="Choose a service category to explore FAQs."
            )

            st.write(f"**Here are some questions you might want to ask about {category}:**")
            random_questions = get_random_questions(category, num=3)
            for q in random_questions:
                st.write(f"- {q['question']}")

        # Input box for the user's question
        with col2:
            st.markdown("<h5 style='color:#2E86C1;'>Ask Your Question:</h5>", unsafe_allow_html=True)
            user_question = st.text_input(
                "Enter your question",
                placeholder="e.g., How does EXL handle data privacy?",
                help="Ask about EXL services or specific details."
            )

        if user_question:
            with st.spinner('Searching for the best match...'):
                answer, score = find_best_match(user_question, qa_data[category])

            if answer:
                # Display predefined knowledge-based answer
                st.success(f"**Answer:** {answer}")
                st.write(f"🔍 **Match Score:** {score}")

                # Offer suggestions for follow-up questions
                follow_up_suggestions = suggest_related_questions(user_question, qa_data[category], threshold=60)
                if follow_up_suggestions:
                    st.write("🤔 **You might also be interested in asking about:**")
                    for suggestion in follow_up_suggestions:
                        st.write(f"- {suggestion}")
            else:
                st.warning("Couldn't find an exact match, generating a model-based answer instead.")

                # Combine context from JSON data and PDF for detailed answer
                context = "\n".join([q["answer"] for q in qa_data[category] if "answer" in q])
                context += "\n" + pdf_text

                detailed_answer, confidence_score = generate_longer_response(user_question, context)

                # Display model-generated answer
                st.info(f"**Model-generated Answer:** {detailed_answer}")
                if confidence_score < 0.5:
                    st.warning(f"The answer might not be entirely relevant. Confidence score: {confidence_score:.2f}")
                else:
                    st.write(f"**Confidence Score:** {confidence_score:.2f}")

                # Suggest follow-up questions based on user input
                follow_up_suggestions = suggest_related_questions(user_question, qa_data[category], threshold=60)
                if follow_up_suggestions:
                    st.write("🔗 **You might also want to ask:**")
                    for suggestion in follow_up_suggestions:
                        st.write(f"- {suggestion}")

        # Show resources for the selected category
        st.subheader("📄 Available Resources")
        if category in resources:
            for resource in resources[category]:
                st.markdown(f"[{resource['label']}]({resource['link']})")

# Email Generation Tab with better layout
with tab2:
    st.sidebar.title("🚀 Tools for Email Generation")
    st.sidebar.subheader("📧 Email Template Generator")

    # Add options for predefined templates and AI-generated emails
    option = st.selectbox("Select Email Generation Option", ["Predefined Templates", "AI-Generated Email"], help="Choose between a template or AI-generated email.")
    
    if option == "Predefined Templates":
        email_generation_ui()  # This will call your email generation UI function

    elif option == "AI-Generated Email":
        st.subheader("✉️ Generate a Personalized Email")
        
        # Create a form for better layout
        with st.form(key="ai_email_form"):
            persona = st.text_input("Persona to target", "", placeholder="e.g., Chief Medical Officer", help="Specify the role or persona.")
            recipient_name = st.text_input("Recipient's Name", "", placeholder="e.g., John Doe", help="The name of the person you're addressing.")
            company_name = st.text_input("Company Name", "", placeholder="e.g., HealthCorp", help="The name of the recipient's company.")
            key_area = st.text_input("Key Area", "", placeholder="e.g., AI-driven analytics, cost management", help="Focus area of your pitch.")
            pain_points = st.text_input("Pain Points", "", placeholder="e.g., Difficulty in managing patient data.", help="Problems or pain points you are addressing.")
            solution = st.text_area("Solution (What EXL Health Offers)", "", placeholder="Explain how EXL Health's services can help.", height=150)
            outcome = st.text_input("Outcome (optional)", "", placeholder="e.g., Improve patient outcomes by 20%")
            cta = st.text_input("Call to Action", "", placeholder="e.g., Can we schedule a call next week to discuss?")
            
            submitted = st.form_submit_button("Generate AI Email")

            if submitted and all([persona, recipient_name, company_name, key_area, solution, cta]):
                with st.spinner("Generating email with AI..."):
                    ai_email = generate_email_with_openai(persona, recipient_name, company_name, key_area, pain_points, solution, outcome, cta)

                if ai_email:
                    st.subheader("✅ AI-Generated Email")
                    st.text_area("Generated Email", ai_email, height=400)
            else:
                st.warning("Please fill in all required fields.")
