class CareerService:
    @staticmethod
    def analyze_resume_ats(student, target_role="Software Engineer"):
        cgpa_score = min(30.0, (student.cgpa / 10.0) * 30.0)
        attendance_score = min(20.0, (student.attendance_percentage / 100.0) * 20.0)
        
        # Skill match simulation based on target role
        base_ats = round(cgpa_score + attendance_score + 35.0, 1)
        
        recommendations = [
            "Add Docker and Kubernetes deployment projects to your resume.",
            "Highlight System Design and Microservices architecture experience.",
            "Include your GitHub repository link with active commits.",
            "Obtain AWS Cloud Practitioner certification to boost ATS rank."
        ]
        
        missing_skills = ["Docker", "Kubernetes", "System Design", "CI/CD Pipelines", "Redis Caching"]
        
        return {
            'ats_score': base_ats,
            'target_role': target_role,
            'readiness_level': 'High' if base_ats >= 80 else ('Medium' if base_ats >= 65 else 'Low'),
            'missing_skills': missing_skills,
            'recommendations': recommendations
        }

    @staticmethod
    def generate_mock_interview_questions(role="Software Engineer"):
        return [
            {"id": 1, "question": "Explain the difference between Process and Thread in Operating Systems.", "category": "Core CS"},
            {"id": 2, "question": "How does Database Indexing work under the hood using B+ Trees?", "category": "Databases"},
            {"id": 3, "question": "Design a Rate Limiter system for an API gateway.", "category": "System Design"},
            {"id": 4, "question": "What happens when you type google.com in your browser?", "category": "Networking"}
        ]
