import json
import glob
import logging
from fuzzywuzzy import fuzz
from transformers import pipeline
import fitz  # PyMuPDF for extracting text from PDFs
import random

# Setup logging for debugging purposes
logging.basicConfig(level=logging.DEBUG)

# Initialize the question-answering pipeline
qa_pipeline = pipeline("question-answering", model="distilbert-base-uncased-distilled-squad")

# Function to load all the Q&A data from JSON files
def load_qa_data():
    """
    Load Q&A data from multiple JSON files into a dictionary categorized by service.
    JSON files should be placed in the 'data/' directory.
    Each JSON should contain a 'service' key and a 'questions' list.
    """
    json_files = glob.glob("data/qa/*.json")  # Find all JSON files in the 'data/' directory
    all_data = {}  # Dictionary to hold all services and their corresponding Q&A
    total_questions = 0  # Initialize a counter for the total number of questions

    for file in json_files:
        with open(file, "r") as f:
            data = json.load(f)
            category = data.get("service")  # Get the service category from the JSON

            # Handle cases where the key might be 'questions' or 'question'
            questions_data = data.get("questions")

            if questions_data:  # If the file contains a 'questions' key
                # Ensure the questions are a list of dictionaries
                if isinstance(questions_data, list):
                    valid_questions = []
                    for question_entry in questions_data:
                        if isinstance(question_entry, dict) and 'question' in question_entry and 'answers' in question_entry:
                            valid_questions.append(question_entry)
                            total_questions += 1
                            logging.debug(f"Loaded question: {question_entry['question']} from service {category}")
                    all_data[category] = valid_questions
                else:
                    logging.warning(f"Invalid 'questions' structure in file {file}. Expected a list, got {type(questions_data).__name__}.")
    
    logging.info(f"Total questions loaded: {total_questions}")
    return all_data

# Function to find the best matching question and answer

def find_best_match(user_question, questions, threshold=70):
    """
    Find the best matching question based on fuzzy string matching.
    Handles questions with or without 'variations' field.
    Returns the best-matching answer and its match score if above the threshold.
    """
    best_match = None
    highest_score = 0
    best_answer = None

    logging.debug(f"Loaded {len(questions)} questions for this category.")

    for entry in questions:
        if "answers" not in entry or not entry["answers"]:  # Skip questions without answers
            logging.warning(f"Skipping question without answer: {entry.get('question', 'No Question')}")
            continue

        # Compare user question with the main question
        score = fuzz.ratio(user_question.lower(), entry["question"].lower())
        logging.debug(f"Score for main question '{entry['question']}': {score}")

        if score > highest_score:
            highest_score = score
            best_match = entry["question"]
            # Concatenate all answers in the 'answers' list
            best_answer = "\n".join(entry["answers"])  # Combine all the answers into a single string

        # If 'variations' field exists, compare the user question with the variations as well
        if "variations" in entry and isinstance(entry["variations"], list):
            for variation in entry["variations"]:
                logging.debug(f"Comparing with variation: {variation}")
                score = fuzz.ratio(user_question.lower(), variation.lower())
                logging.debug(f"Score for variation '{variation}': {score}")
                if score > highest_score:
                    highest_score = score
                    best_match = variation
                    best_answer = "\n".join(entry["answers"])  # Combine all the answers into a single string

    logging.debug(f"Best match: {best_match} with score: {highest_score}")

    if highest_score >= threshold:
        return best_answer, highest_score

    return None, highest_score

# Function to generate a longer response using the QA pipeline
def generate_longer_response(question, context):
    """
    Generate a detailed response using the QA model with a provided context.
    """
    try:
        result = qa_pipeline(question=question, context=context)
        return result['answer'], result['score']
    except Exception as e:
        logging.error(f"Error generating longer response: {e}")
        return None, 0.0

# Function to extract text from PDF files using PyMuPDF
def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file using PyMuPDF (fitz).
    """
    text = ""
    try:
        doc = fitz.open(pdf_path)  # Open the PDF
        for page in doc:
            text += page.get_text()  # Extract text from each page
        return text
    except Exception as e:
        logging.error(f"Error extracting text from PDF: {str(e)}")
        return ""

# Function to suggest related questions based on fuzzy matching
def suggest_related_questions(user_question, questions, threshold=60, num_suggestions=3):
    """
    Suggest related questions based on fuzzy matching.
    """
    suggestions = []
    
    for entry in questions:
        # Ensure the entry contains a 'question' field before accessing it
        if 'question' in entry:
            score = fuzz.partial_ratio(user_question.lower(), entry['question'].lower())
            if score >= threshold:
                suggestions.append(entry['question'])
    
    # Return the top 'num_suggestions' suggestions
    return random.sample(suggestions, min(len(suggestions), num_suggestions))
