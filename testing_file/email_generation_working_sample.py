import streamlit as st
import json
import openai
import random
import os

# Set your OpenAI API key here (replace 'your-openai-api-key' with your actual API key)
openai.api_key = "your-openai-api-key"

# Function to load email templates from all available JSON files in the 'data/' directory
def load_email_templates():
    templates = []
    data_folder = 'data/emails'  # Path to your data folder containing JSON files for each category

    for file_name in os.listdir(data_folder):
        if file_name.endswith('.json'):
            with open(os.path.join(data_folder, file_name), 'r') as file:
                try:
                    data = json.load(file)
                    # Assuming the data has categories as keys and lists of templates as values
                    for category, category_templates in data.items():
                        if isinstance(category_templates, list):
                            templates.extend(category_templates)  # Combine all templates across categories
                        else:
                            st.error(f"Error: The category '{category}' in file '{file_name}' does not contain a list of templates.")
                except json.JSONDecodeError:
                    st.error(f"Error: Could not parse the JSON file '{file_name}'.")
    return templates

# Function to generate email content with slight variations and user inputs
def generate_email_content(template, recipient_name, company_name, service_name, your_name, your_title, contact_info, cta, testimonials, additional_services):
    subject_variations = [
        template.get('subject', 'EXL Health Solutions'),
        f"Discover EXL’s {service_name} for {company_name}",
        f"How {company_name} can benefit from EXL’s {service_name}",
        f"{company_name} Strategy Boost: EXL’s {service_name}",
        f"Leverage {service_name} to achieve goals at {company_name}"
    ]
    # Randomly pick a subject variation
    subject = random.choice(subject_variations)

    body_variations = [
        template.get('body', ''),
        template['body'].replace("I’d love to explore", "Let's discuss how we can"),
        template['body'].replace("Could we schedule a brief call?", f"{cta or 'Let’s book a time to connect.'}"),
        template['body'].replace("drive operational efficiencies", "enhance performance metrics"),
        template['body'].replace("[Service]", additional_services or "[Service]")  # Use additional services if provided
    ]
    # Randomly pick a body variation
    body = random.choice(body_variations)

    # Insert the testimonials if provided
    if testimonials:
        body += f"\n\nTestimonial: {testimonials}"

    return subject, body.replace("[Recipient's Name]", recipient_name or "[Recipient's Name]") \
        .replace("[Company Name]", company_name or "[Company Name]") \
        .replace("[Service]", service_name or "[Service]") \
        .replace("[Your Name]", your_name or "[Your Name]") \
        .replace("[Your Title]", your_title or "[Your Title]") \
        .replace("[Your Contact Information]", contact_info or "[Your Contact Information]")

# Function to generate AI email using OpenAI GPT-3.5 (optional)
def generate_email_with_openai(service_name, recipient_name, company_name, your_name, your_title, contact_info, cta, testimonials):
    try:
        email_context = f"""
        Service: {service_name}
        Recipient: {recipient_name}
        Company: {company_name}
        From: {your_name} ({your_title}, {contact_info})
        CTA: {cta}
        Testimonials: {testimonials}
        """

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # You can use GPT-4 if available
            messages=[
                {"role": "system", "content": "You are an email writing assistant."},
                {"role": "user", "content": f"Write an email for the following context: {email_context}"}
            ],
            max_tokens=300
        )
        email_content = response['choices'][0]['message']['content']
        return email_content
    except Exception as e:
        return f"Error generating email with OpenAI: {str(e)}"

# Main function for the email generation UI
def email_generation_ui():
    st.title("Email Template Generator")

    # Load all templates from multiple JSON files
    templates = load_email_templates()
    if not templates:
        st.warning("No email templates found.")
        return

    # Customization inputs (input once and apply to all emails)
    recipient_name = st.text_input("Recipient's Name", "", key="recipient_name")
    company_name = st.text_input("Recipient's Company", "", key="company_name")
    your_name = st.text_input("Your Name", "", key="your_name")
    your_title = st.text_input("Your Title", "", key="your_title")
    contact_info = st.text_input("Your Contact Information", "", key="contact_info")

    # New Inputs for CTA, Testimonials, and Additional Services
    cta = st.text_input("Call-to-Action (CTA)", "Can we schedule a call next week?", key="cta")
    testimonials = st.text_area("Testimonials (Optional)", "Here's what one of our clients said...", key="testimonials")
    additional_services = st.text_input("Additional Services (Optional)", "", key="additional_services")

    num_variations = st.slider("How many email variations to generate?", min_value=1, max_value=50, value=5)

    if st.button("Generate Emails", key="generate_email_button"):
        for idx in range(num_variations):
            # Randomly select any template from the available templates
            template = random.choice(templates)

            # Check if template is a dictionary and contains required keys
            if isinstance(template, dict) and 'service_category' in template:
                subject, email_content = generate_email_content(
                    template,
                    recipient_name,
                    company_name,
                    template['service_category'],
                    your_name,
                    your_title,
                    contact_info,
                    cta,
                    testimonials,
                    additional_services
                )
                st.subheader(f"Generated Email {idx+1} - {subject}")
                st.text_area(f"Email Body {idx+1}", email_content, height=300)

                # Option to generate AI-based email content
                if st.button(f"Generate AI Email {idx}", key=f"generate_ai_email_{idx}"):
                    ai_email = generate_email_with_openai(
                        template['service_category'],
                        recipient_name,
                        company_name,
                        your_name,
                        your_title,
                        contact_info,
                        cta,
                        testimonials
                    )
                    st.subheader(f"AI-Generated Email {idx+1}")
                    st.text_area(f"AI Email Body {idx+1}", ai_email, height=300)
            else:
                st.error(f"Invalid template structure or missing 'service_category' key in template: {template}")

# Run the app
if __name__ == "__main__":
    email_generation_ui()
