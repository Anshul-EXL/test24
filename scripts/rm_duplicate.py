import json

# Step 2: Remove Duplicate Questions
def remove_duplicates(input_file, output_file):
    with open(input_file, 'r') as f:
        questions_data = json.load(f)

    unique_questions = []
    seen_questions = set()  # To track unique questions

    for item in questions_data:
        question = item["question"].lower()  # Convert to lowercase for case-insensitive comparison
        if question not in seen_questions:
            unique_questions.append(item)
            seen_questions.add(question)  # Mark this question as seen

    # Save the unique questions to a new file
    with open(output_file, 'w') as f:
        json.dump(unique_questions, f, indent=4)
    print(f"Saved {len(unique_questions)} unique questions to {output_file}")

# Run the duplication removal script
remove_duplicates("generated_questions.json", "unique_questions.json")
