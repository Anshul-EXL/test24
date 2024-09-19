import json
import random

# Define personas and their characteristics
personas = {
    "CEO": {
        "tone": "professional",
        "pain_points": [
            "Cost management",
            "Operational inefficiencies",
            "Strategic growth"
        ]
    },
    "CTO": {
        "tone": "casual",
        "pain_points": [
            "Technology integration",
            "Data security"
        ]
    },
    "CFO": {
        "tone": "professional",
        "pain_points": [
            "Financial oversight",
            "Regulatory compliance"
        ]
    },
    "Director of Care Management": {
        "tone": "informative",
        "pain_points": [
            "Patient engagement",
            "Quality improvement"
        ]
    },
    "Chief Medical Officer": {
        "tone": "professional",
        "pain_points": [
            "Clinical outcomes",
            "Patient safety"
        ]
    },
    "Operations Manager": {
        "tone": "casual",
        "pain_points": [
            "Process efficiency",
            "Resource allocation"
        ]
    },
    "IT Manager": {
        "tone": "informative",
        "pain_points": [
            "System integration",
            "Data analytics"
        ]
    },
    "Quality Improvement Manager": {
        "tone": "professional",
        "pain_points": [
            "Regulatory compliance",
            "Patient care standards"
        ]
    }
}

# Define services and corresponding email content
services = {
    "Utilization Management": "We optimize healthcare resources to reduce costs and improve patient outcomes.",
    "Population & Risk Analytics": "Our analytics solutions provide insights that help manage population health effectively.",
    "AI-driven Solutions": "Integrate cutting-edge AI technology to streamline operations and enhance service delivery.",
    "Contact Center Solutions": "Improve patient interactions with advanced contact center technology.",
    "Care Management": "Comprehensive care management solutions to enhance patient support and engagement.",
    "Cost Reduction Strategies": "Identify and implement strategies to reduce operational costs.",
    "Digital Transformation": "Transition to digital platforms to enhance efficiency and patient experiences.",
    "Compliance Management": "Ensure adherence to healthcare regulations and minimize risks."
}

# Generate unique subject lines based on persona and service
def generate_subject_line(persona, service):
    subject_lines = {
        "CEO": [
            "Transform Your Bottom Line with Strategic Cost Management",
            "Unlock Growth Potential: Explore Our Utilization Management Solutions",
            "Drive Operational Efficiency: The Key to Sustainable Success",
            "Maximize ROI with Our Advanced Risk Analytics",
            "Achieve Strategic Goals with Tailored Healthcare Solutions"
        ],
        "CTO": [
            "Harness AI to Elevate Your Technology Framework",
            "Integrate Seamlessly: Solutions for a Digital-First Future",
            "Secure Your Data with Innovative Contact Center Solutions",
            "Future-Proof Your Operations with AI-Driven Insights",
            "Revolutionize Healthcare Tech: The Power of Integration"
        ],
        "CFO": [
            "Elevate Financial Oversight: Strategies for Cost Reduction",
            "Ensure Compliance and Save Costs with Our Solutions",
            "Transform Your Financial Strategy with Our Care Management Services",
            "Reduce Operational Costs: Proven Strategies for CFOs",
            "Achieve Financial Excellence Through Effective Resource Management"
        ],
        "Director of Care Management": [
            "Enhance Patient Engagement with Our Comprehensive Care Solutions",
            "Transform Quality Improvement Initiatives: Let's Connect!",
            "Improve Patient Outcomes with Targeted Care Management",
            "Strategies for Enhancing Quality Standards in Healthcare",
            "Engage Patients Effectively: Discover Our Proven Solutions"
        ],
        "Chief Medical Officer": [
            "Prioritize Patient Safety: Our Proven Clinical Solutions",
            "Enhance Clinical Outcomes: Innovative Strategies for CMOs",
            "Drive Quality Care Initiatives with Our Expertise",
            "Empower Your Team with Advanced Care Management Tools",
            "Achieve Excellence in Clinical Performance: Explore Our Services"
        ],
        "Operations Manager": [
            "Streamline Your Operations: Innovative Solutions Await",
            "Optimize Resources: Strategies for Efficiency and Growth",
            "Enhance Process Efficiency: The Tools You Need",
            "Boost Productivity with Our Contact Center Solutions",
            "Transform Your Operations with Proven Strategies"
        ],
        "IT Manager": [
            "Integrate Data Analytics for Smarter Decision Making",
            "Streamline System Integration: Solutions Tailored for You",
            "Elevate Your IT Strategy with AI-Driven Solutions",
            "Unlock the Power of Data: Insights for Healthcare Success",
            "Optimize Your Systems: Innovative Solutions Await"
        ],
        "Quality Improvement Manager": [
            "Achieve Compliance: Proven Strategies for Quality Leaders",
            "Elevate Patient Care Standards: Let's Connect",
            "Enhance Your Quality Initiatives with Our Expertise",
            "Drive Quality Improvement with Effective Solutions",
            "Empower Your Team: Achieve Excellence in Care Standards"
        ]
    }
    return random.choice(subject_lines[persona])

# Variations for email bodies
def generate_email_body(persona, service, pain_point):
    body_variations = {
        "CEO": [
            f"As the {persona} of [Company_Name], you are undoubtedly aware of the challenges surrounding {pain_point}. "
            f"At EXL Health, we specialize in {service}, which can greatly assist you in addressing this issue. "
            f"{services[service]} I’d love to discuss how our services can align with your strategic goals. Can we schedule a 30-minute call to dive deeper?",

            f"Dear [Recipient_Name],\n\nIn today's fast-paced healthcare landscape, {pain_point} is a significant challenge. "
            f"At EXL Health, we offer {service} solutions designed to optimize your operations. {services[service]} "
            f"Let's connect to discuss how we can help you achieve your goals. I've attached a case study for your review."
        ],
        "CTO": [
            f"Hi [Recipient_Name],\n\nI hope you're doing well! I noticed that {pain_point} is a big focus for you at [Company_Name]. "
            f"At EXL Health, we have some cool solutions in {service} that could really help. {services[service]} "
            f"Let’s chat soon? I’d love to hear your thoughts! Also, I've included a testimonial from a recent project.",
            
            f"Hey [Recipient_Name],\n\nAs a CTO, I know you're tackling {pain_point} daily. "
            f"At EXL Health, we specialize in {service}, which could be a game-changer for you. {services[service]} "
            f"Let's schedule a quick call or block some time on your calendar!"
        ],
        "CFO": [
            f"Dear [Recipient_Name],\n\nAs the CFO of [Company_Name], managing {pain_point} is crucial for your success. "
            f"EXL Health offers {service} strategies that can help you navigate these challenges. {services[service]} "
            f"Can we find a time to discuss? I’ve attached a relevant case study for your reference.",
            
            f"Hello [Recipient_Name],\n\nI understand that {pain_point} is a priority for you. "
            f"At EXL Health, we provide effective {service} solutions to enhance financial performance. "
            f"{services[service]} I’d love to connect and discuss this further over a quick call."
        ],
        "Director of Care Management": [
            f"Hello [Recipient_Name],\n\nImproving {pain_point} is essential for your role. "
            f"Our expertise in {service} can provide valuable insights and support. {services[service]} "
            f"I’d be happy to share case studies and success stories. Could we find a time to connect and discuss a recent project?",
            
            f"Hi [Recipient_Name],\n\nAs a Director of Care Management, you're focused on {pain_point}. "
            f"At EXL Health, we offer {service} solutions to enhance patient engagement. {services[service]} "
            f"Let’s chat about how we can support your initiatives. I’ve attached a case study for you."
        ],
        "Chief Medical Officer": [
            f"Dear [Recipient_Name],\n\nPrioritizing patient safety is key for you as a CMO. "
            f"At EXL Health, our {service} can help enhance clinical outcomes. {services[service]} "
            f"I'd love to discuss how we can work together and share a case study that highlights our success.",
            
            f"Hello [Recipient_Name],\n\nAs Chief Medical Officer, you face challenges around {pain_point}. "
            f"At EXL Health, we specialize in {service} to improve patient safety. {services[service]} "
            f"Can we schedule a call to explore this? I've included a testimonial from a healthcare leader."
        ],
        "Operations Manager": [
            f"Hi [Recipient_Name],\n\nI hope you're having a great day! I wanted to touch base regarding {pain_point}. "
            f"At EXL Health, we provide {service} solutions that can streamline your operations. {services[service]} "
            f"Let’s connect soon or block some time on your calendar!",
            
            f"Hello [Recipient_Name],\n\nAs an Operations Manager, you know how vital it is to address {pain_point}. "
            f"EXL Health's {service} can enhance your efficiency. {services[service]} Let's discuss a recent project that might interest you."
        ],
        "IT Manager": [
            f"Hello [Recipient_Name],\n\nIntegrating new technologies can be challenging, especially with {pain_point}. "
            f"At EXL Health, we offer {service} to help streamline your processes. {services[service]} "
            f"Can we schedule a time to chat? I’ve attached a case study for your review.",
            
            f"Hi [Recipient_Name],\n\nI noticed that {pain_point} is a significant focus for you. "
            f"At EXL Health, we specialize in {service}, which can provide the insights you need. {services[service]} "
            f"Let’s connect for a quick chat or review a recent success story together."
        ],
        "Quality Improvement Manager": [
            f"Dear [Recipient_Name],\n\nAchieving compliance and high patient care standards is crucial. "
            f"EXL Health can help with our {service}. {services[service]} I'd love to discuss this further and share a recent case study.",
            
            f"Hello [Recipient_Name],\n\nAs a Quality Improvement Manager, you focus on {pain_point}. "
            f"At EXL Health, we offer {service} solutions to enhance quality. {services[service]} "
            f"Can we find a time to talk? I've included testimonials from healthcare professionals."
        ]
    }
    return random.choice(body_variations[persona])

# Generate email samples
def generate_email_samples(num_samples):
    email_samples = []

    for _ in range(num_samples):
        persona = random.choice(list(personas.keys()))
        persona_info = personas[persona]
        
        # Randomly select a pain point and a service
        pain_point = random.choice(persona_info["pain_points"])
        service = random.choice(list(services.keys()))
        
        # Generate unique subject line
        subject_line = generate_subject_line(persona, service)

        # Generate email content based on persona
        email_body = generate_email_body(persona, service, pain_point)

        # Adding personalization elements
        email_body = email_body.replace("[Recipient_Name]", random.choice(["Alice", "Bob", "Carol"]))
        email_body = email_body.replace("[Company_Name]", random.choice(["HealthCorp", "Medico", "Wellness Inc."]))
        email_body = email_body.replace("[Your Name]", "Your Name")

        # Append to email samples
        email_samples.append({
            "persona": persona,
            "email_body": email_body,
            "service": service,
            "subject_line": subject_line
        })

    return email_samples

# Generate a random number of email samples between 2000 and 3000
num_samples = random.randint(2000, 3000)
email_samples = generate_email_samples(num_samples)

# Save the email samples to a JSON file
with open('clinical_service_email_samples.json', 'w') as json_file:
    json.dump(email_samples, json_file, indent=4)

print(f"Generated {num_samples} email samples and saved to clinical_service_email_samples.json")
