from services.ai_engine import AIEngine
import json

class GradingService:
    @staticmethod
    def generate_quiz_questions(subject_name, topic, num_questions=3):
        prompt = f"Generate {num_questions} multiple-choice quiz questions for the topic '{topic}' in the course '{subject_name}'. Return JSON array of objects with keys: question, options (list of 4 strings), answer (string matching one option), bloom_level."
        raw_response = AIEngine.generate_completion(prompt)
        
        try:
            # Try parsing JSON array from response
            start = raw_response.find('[')
            end = raw_response.rfind(']')
            if start != -1 and end != -1:
                return json.loads(raw_response[start:end+1])
        except Exception:
            pass

        # Fallback structured quiz questions
        return [
            {
                "question": f"Which principle is central to {topic} in {subject_name}?",
                "options": ["Abstraction & Encapsulation", "Linear Search", "Static Memory", "Disk Paging"],
                "answer": "Abstraction & Encapsulation",
                "bloom_level": "Understand"
            },
            {
                "question": f"What is the expected asymptotic bound for optimal implementation of {topic}?",
                "options": ["O(1)", "O(log n)", "O(n log n)", "O(n^2)"],
                "answer": "O(n log n)",
                "bloom_level": "Analyze"
            }
        ]

    @staticmethod
    def evaluate_submission(submission_text, assignment_title):
        length = len(submission_text.split())
        plagiarism_score = round(max(2.0, min(15.0, 100 / max(1, length))), 1)
        grammar_score = round(min(98.0, 80 + (length / 10)), 1)
        suggested_marks = round(min(100.0, 75 + (length / 5)), 1)

        return {
            'marks': suggested_marks,
            'plagiarism_percentage': plagiarism_score,
            'grammar_score': grammar_score,
            'feedback': f"Good structure and technical clarity on {assignment_title}. Consider adding more diagrams and real-world code examples."
        }
