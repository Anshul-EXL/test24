import streamlit as st
import json
import openai
import random
import os

# Set your OpenAI API key here
openai.api_key = "your-openai-api-key"

# Function to load email templates from all available JSON files in the 'data/' directory
def load_email_templates():
    templates = {}
    data_folder = 'data/emails'  # Path to your data folder containing JSON files for each category

    for file_name in os.listdir(data_folder):
        if file_name.endswith('.json'):
            with open(os.path.join(data_folder, file_name), 'r') as file:
                try:
                    data = json.load(file)
                    # Combine categories and templates from multiple files
                    for category, category_templates in data.items():
                        if isinstance(category_templates, list):
                            if category not in templates:
                                templates[category] = []  # Initialize category if not exists
                            templates[category].extend(category_templates)  # Add templates to the category
                        else:
                            st.error(f"Error: The category '{category}' in file '{file_name}' does not contain a list of templates.")
                except json.JSONDecodeError:
                    st.error(f"Error: Could not parse the JSON file '{file_name}'.")
    return templates

# Function to generate email content with user inputs
def generate_email_content(template, recipient_name, recipient_title, company_name, service_name, pain_points, key_metrics, case_study_name, case_study_outcome, testimonial, cta, your_name, your_title, contact_info):
    subject = template.get('subject', 'EXL Health Solutions').replace("[Service Name]", service_name)

    body = template.get('body', '').replace("[Recipient's Name]", recipient_name or "[Recipient's Name]") \
        .replace("[Recipient's Title]", recipient_title or "[Recipient's Title]") \
        .replace("[Company Name]", company_name or "[Company Name]") \
        .replace("[Service Name]", service_name or "[Service Name]") \
        .replace("[Pain Points]", pain_points or "[Pain Points]") \
        .replace("[Key Metrics]", key_metrics or "[Key Metrics]") \
        .replace("[Case Study Name]", case_study_name or "[Case Study Name]") \
        .replace("[Case Study Outcome]", case_study_outcome or "[Case Study Outcome]") \
        .replace("[Testimonial]", testimonial or "[Testimonial]") \
        .replace("[CTA]", cta or "[CTA]") \
        .replace("[Your Name]", your_name or "[Your Name]") \
        .replace("[Your Title]", your_title or "[Your Title]") \
        .replace("[Your Contact Information]", contact_info or "[Your Contact Information]")

    return subject, body

# Main function for the email generation UI
def email_generation_ui():
    st.title("Email Template Generator")

    # Load all templates from multiple JSON files
    templates = load_email_templates()
    if not templates:
        st.warning("No email templates found.")
        return

    # Add category selection dropdown
    category_options = list(templates.keys())  # Get all available categories
    selected_category = st.selectbox("Select a Main Category", category_options)

    if selected_category:
        # Filter templates by the selected category
        selected_templates = templates.get(selected_category, [])

        # Get available service categories for the selected main category
        service_categories = list(set([template['service_category'] for template in selected_templates]))

        # Add service category selection dropdown
        selected_service_category = st.selectbox("Select a Service Category", service_categories)

        if selected_service_category:
            # Filter templates by the selected service category
            filtered_templates = [template for template in selected_templates if template['service_category'] == selected_service_category]

            if not filtered_templates:
                st.warning(f"No templates found for the selected service category: {selected_service_category}")
                return

            # Customization inputs (input once and apply to all emails)
            st.subheader("Company and Contact Information")
            recipient_name = st.text_input("Recipient's Name", "", key="recipient_name")
            recipient_title = st.text_input("Recipient's Title", "", key="recipient_title")
            company_name = st.text_input("Company Name", "", key="company_name")
            service_name = st.text_input("Service Name (e.g., Utilization Management)", selected_service_category, key="service_name")

            st.subheader("Pain Points & Case Study")
            pain_points = st.text_area("Pain Points (e.g., Cost Management, Operational Inefficiencies)", "", key="pain_points")
            key_metrics = st.text_input("Key Metrics (e.g., 20% reduction in costs)", "", key="key_metrics")
            case_study_name = st.text_input("Case Study Name", "", key="case_study_name")
            case_study_outcome = st.text_input("Case Study Outcome", "", key="case_study_outcome")

            st.subheader("Call-to-Action & Testimonial")
            testimonial = st.text_area("Testimonial", "Here's what one of our clients said...", key="testimonial")
            cta = st.text_input("Call-to-Action (CTA)", "Can we schedule a call next week?", key="cta")

            st.subheader("Your Information")
            your_name = st.text_input("Your Name", "", key="your_name")
            your_title = st.text_input("Your Title", "", key="your_title")
            contact_info = st.text_input("Your Contact Information", "", key="contact_info")

            num_variations = st.slider("How many email variations to generate?", min_value=1, max_value=50, value=5)

            if st.button("Generate Emails", key="generate_email_button"):
                for idx in range(num_variations):
                    # Randomly select any template from the available templates in the selected service category
                    if filtered_templates:  # Ensure there are templates available
                        template = random.choice(filtered_templates)

                        # Check if template is a dictionary and contains required keys
                        if isinstance(template, dict) and 'service_category' in template:
                            subject, email_content = generate_email_content(
                                template,
                                recipient_name,
                                recipient_title,
                                company_name,
                                service_name,
                                pain_points,
                                key_metrics,
                                case_study_name,
                                case_study_outcome,
                                testimonial,
                                cta,
                                your_name,
                                your_title,
                                contact_info
                            )
                            st.subheader(f"Generated Email {idx + 1} - {subject}")
                            st.text_area(f"Email Body {idx + 1}", email_content, height=300)
                        else:
                            st.error(f"Invalid template structure or missing 'service_category' key in template: {template}")
                    else:
                        st.error(f"No templates found for the selected service category: {selected_service_category}")

# Run the app
if __name__ == "__main__":
    email_generation_ui()
