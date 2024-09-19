import json
import random
import time


# Step 1: Generate Question Variations
def generate_question_variations(qa_pairs, target_count):
    generated_questions = []
    
    while len(generated_questions) < target_count:
        for qa_pair in qa_pairs:
            for question_variation in qa_pair["question_variations"]:
                generated_questions.append({
                    "question": question_variation,
                    "answer": qa_pair["answer"]
                })
                
                if len(generated_questions) >= target_count:
                    break  # Stop when the target count is reached

            if len(generated_questions) >= target_count:
                break  # Stop when the target count is reached
    
    return generated_questions

# Save the generated questions as a temporary JSON file
def save_questions_to_file(generated_questions, file_name="generated_questions.json"):
    with open(file_name, 'w') as f:
        json.dump(generated_questions, f, indent=4)
    print(f"Saved {len(generated_questions)} questions to {file_name}")

# Define questions with short, direct phrasing and long answers for each category based on the EXL Clinical Services data
qa_pairs = [
    # Clinical Services Overview
    {
        "question_variations": [
            "What are EXL Clinical Services?",
            "Can you explain EXL's Clinical Services?",
            "What does EXL offer in Clinical Services?",
            "Tell me more about EXL's clinical services.",
            "What are the key clinical services provided by EXL?"
        ],
        "answer": ("EXL Clinical Services focus on optimizing healthcare operations and improving clinical outcomes for health plans and provider organizations. "
                   "We enable digital transformation, enhance care management, and turn raw data into actionable insights, helping clients achieve better member outcomes "
                   "and operational efficiencies.")
    },
    
    # Pain Points We Solve
    {
        "question_variations": [
            "What problems do EXL Clinical Services solve?",
            "How can EXL help with healthcare challenges?",
            "What pain points does EXL address?",
            "How does EXL solve common healthcare issues?",
            "What are the main pain points EXL addresses in healthcare?"
        ],
        "answer": ("EXL Clinical Services solve several critical pain points in healthcare, including: "
                   "\n• Cost Management: Reducing healthcare costs through efficient utilization management and care coordination. "
                   "\n• Operational Inefficiencies: Streamlining clinical workflows to enhance operational performance and reduce administrative burdens. "
                   "\n• Quality Gaps: Improving patient care by identifying and managing clinical, social, and behavioral health gaps. "
                   "\n• Regulatory Compliance: Ensuring adherence to healthcare regulations and minimizing the risk of penalties. "
                   "\n• Member Engagement: Enhancing member and provider satisfaction through improved communication and engagement strategies.")
    },

    # Who We Serve
    {
        "question_variations": [
            "Who benefits from EXL Clinical Services?",
            "Which companies does EXL serve?",
            "Who does EXL work with?",
            "What types of clients use EXL Clinical Services?",
            "Who are the typical customers for EXL?"
        ],
        "answer": ("EXL serves health plan payers and provider organizations, offering solutions that empower healthcare managers to focus on improving member outcomes, "
                   "containing costs, and ensuring the best experience for both members and providers. Our clients include health plan payers and provider organizations.")
    },

    # Utilization Management (UM)
    {
        "question_variations": [
            "What is EXL's utilization management service?",
            "How does EXL provide utilization management?",
            "Tell me about EXL’s utilization management solutions.",
            "What are the key features of EXL’s utilization management service?",
            "What does EXL's utilization management include?"
        ],
        "answer": ("EXL’s Utilization Management (UM) service ensures that healthcare services are used appropriately, efficiently, and effectively to manage costs while maintaining high-quality care. "
                   "Key features include pre-authorization, concurrent review, post-service clinical claims review, and appeals and denials management. These services help optimize the delivery of healthcare resources, "
                   "improve quality outcomes, and manage costs efficiently.")
    },

    # Care Management
    {
        "question_variations": [
            "What is care management?",
            "What does care management involve?",
            "How does EXL provide care management?",
            "What are EXL's care management services?",
            "Can you explain care management at EXL?"
        ],
        "answer": ("EXL Health provides end-to-end care management services that cover both medical and behavioral health. These include member screening, risk assessment, outreach, and care planning. "
                   "EXL's care management services help healthcare organizations coordinate care, manage adherence, and collaborate with providers, improving patient outcomes while optimizing resource use.")
    },

    # Population & Risk Analytics
    {
        "question_variations": [
            "What is population & risk analytics?",
            "How does EXL use risk analytics?",
            "What are EXL’s population analytics?",
            "Can you explain population and risk analytics?",
            "How does EXL leverage population analytics?"
        ],
        "answer": ("EXL's population & risk analytics enable healthcare organizations to get a complete view of their patient population. By identifying high-risk members, EXL helps prioritize outreach and improve care coordination. "
                   "These analytics also support organizations in designing value-based benefit models, improving network performance, and reducing costs by preventing unnecessary hospitalizations and procedures.")
    },

    # Digital and Automation Technology
    {
        "question_variations": [
            "How does EXL use digital automation?",
            "What digital solutions does EXL offer?",
            "How does EXL use technology in healthcare?",
            "What role does automation play in EXL’s services?",
            "How does EXL implement automation?"
        ],
        "answer": ("EXL Health integrates cutting-edge digital technologies including AI, machine learning, and automation into healthcare workflows. These technologies reduce cycle times, enhance operational accuracy, and drive cost savings. "
                   "By automating manual tasks and improving engagement with members and providers, EXL helps healthcare organizations optimize their clinical operations and achieve better outcomes.")
    },

    # Global Delivery and Staffing
    {
        "question_variations": [
            "What is EXL’s global delivery model?",
            "How does EXL manage global staffing?",
            "What staffing models does EXL use?",
            "What are EXL’s delivery and staffing models?",
            "How does EXL staff its healthcare services?"
        ],
        "answer": ("EXL Health operates a flexible global delivery model with onshore, offshore, and work-from-home options. With over 2,100 clinical resources available, EXL scales staffing based on client needs. "
                   "EXL’s global centers ensure timely and cost-efficient delivery of services, while specialized training programs keep teams updated on industry standards and regulatory requirements.")
    },

    # Compliance and Accreditation
    {
        "question_variations": [
            "What accreditations does EXL have?",
            "How does EXL ensure compliance?",
            "Is EXL accredited?",
            "How does EXL handle regulatory compliance?",
            "What certifications does EXL hold?"
        ],
        "answer": ("EXL Health maintains industry-recognized certifications such as URAC accreditation to ensure the highest quality of service in care management and utilization management. EXL follows strict regulatory compliance protocols to meet healthcare regulations and ensure operational excellence.")
    },

    # Client Success Stories and Outcomes
    {
        "question_variations": [
            "What success stories do you have?",
            "Can you share a case study?",
            "What outcomes has EXL achieved?",
            "Can you provide an example of EXL’s impact?",
            "What are some of EXL's success stories?"
        ],
        "answer": ("EXL has achieved remarkable results for healthcare clients. For example, EXL helped a regional health plan implement a fully accredited utilization management program, resulting in a 30% increase in in-network care and a 10% reduction in readmissions. "
                   "EXL’s solutions have consistently led to reduced hospitalizations, improved quality of care, and significant cost savings for healthcare providers.")
    },

    # Financial Benefits and Cost Reduction
    {
        "question_variations": [
            "How does EXL help reduce costs?",
            "What financial benefits does EXL offer?",
            "How does EXL manage costs?",
            "Can EXL help with cost savings?",
            "What are the cost benefits of EXL’s services?"
        ],
        "answer": ("EXL helps healthcare organizations achieve cost savings through utilization management, automation, and advanced analytics. By reducing unnecessary treatments and improving care coordination, EXL drives down operational costs while maintaining quality. "
                   "Clients have also reported enhanced revenue optimization through EXL’s population & risk analytics and value-based models.")
    },

    # Training and Development Programs
    {
        "question_variations": [
            "What training does EXL provide?",
            "How does EXL train its staff?",
            "What are your training programs?",
            "How do you ensure staff are well-trained?",
            "Can you explain EXL’s staff development programs?"
        ],
        "answer": ("EXL provides comprehensive training for its clinical staff through its proprietary Healthcare and Customer Experience Academies. These programs focus on the latest industry practices, compliance standards, and client-specific requirements. "
                   "EXL also offers ongoing education to ensure its staff stays up to date with emerging trends and regulations in the healthcare industry.")
    },

    # Resources (Website, Solution Sheet, Use Cases)
    {
        "question_variations": [
            "Where can I find more information about EXL Clinical Services?",
            "Do you have any solution sheets or resources for EXL Clinical Services?",
            "Where can I access EXL’s case studies or solution sheets?",
            "Can you provide links to EXL’s clinical services?",
            "What resources are available for learning more about EXL Clinical Services?"
        ],
        "answer": ("You can explore EXL’s Clinical Services through the following key resources: "
                   "\n• Website: [EXL Clinical Services](https://www.exlservice.com/industries/health-and-life-sciences/clinical-services) "
                   "\n• Solution Sheet: [Download Clinical Services Solution Sheet](https://info1.exlservice.com/hubfs/Media-Library/insights/solution-sheet/EXL_SS_Clinical%20Services.pdf) "
                   "\n• Use Cases: [Clinical Services Use Cases](https://info1.exlservice.com/hubfs/Media-Library/insights/solution-sheet/EXL_SS_Clinical%20Services.pdf)")
    },

    # Why Partner with EXL
    {
        "question_variations": [
            "Why should we partner with EXL?",
            "What makes EXL the best partner for clinical services?",
            "Why choose EXL for clinical services?",
            "What are the benefits of partnering with EXL?",
            "What sets EXL apart as a healthcare partner?"
        ],
        "answer": ("Partnering with EXL brings significant benefits due to our deep analytical expertise, innovative digital solutions, and global delivery model. "
                   "We leverage data from over 260 million lives to provide actionable insights, and our platform integrates cloud technologies, NLP, machine learning, and automation to enhance operational efficiency. "
                   "With over 2,100 clinical resources across 14 global delivery centers, EXL offers flexible, compliant service delivery, delivering tangible improvements in care management and operational efficiencies.")
    },

    # Personas We Target (example for CMO)
    {
        "question_variations": [
            "How can EXL help a Chief Medical Officer (CMO)?",
            "What does EXL offer for Chief Medical Officers?",
            "What are the benefits for a CMO partnering with EXL?",
            "How can EXL’s solutions benefit a Chief Medical Officer?",
            "Why should a CMO work with EXL?"
        ],
        "answer": ("EXL offers tailored solutions for Chief Medical Officers (CMOs), focusing on improving clinical outcomes and ensuring quality improvement. "
                   "With our advanced analytics and care management solutions, CMOs can ensure efficient care coordination, streamline clinical operations, and enhance patient outcomes, all while reducing operational costs.")
    }
]

# Generate 5,000-6,000 question variations
target_count = 6000
generated_questions = generate_question_variations(qa_pairs, target_count)

# Save the generated question variations to a JSON file
save_questions_to_file(generated_questions, "generated_questions.json")