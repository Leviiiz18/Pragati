from models import User, AttendanceRecord, ExamResult, FeeRecord, AIRiskAlert, db
from datetime import datetime, timedelta

class RiskAnalyticsService:
    @staticmethod
    def calculate_student_risk(student_id):
        student = User.query.get(student_id)
        if not student or student.role != 'student':
            return 0.0, []

        reasons = []
        score = 0.0

        # 1. Attendance Check
        if student.attendance_percentage < 75:
            diff = 75 - student.attendance_percentage
            score += min(40, diff * 2.5)
            reasons.append(f"Low attendance ({student.attendance_percentage}%) below 75% mandatory threshold.")

        # 2. CGPA Check
        if student.cgpa < 6.5:
            score += (6.5 - student.cgpa) * 15
            reasons.append(f"Low CGPA ({student.cgpa}) indicates academic struggle.")

        # 3. Fee Delay Check
        fee = FeeRecord.query.filter_by(student_id=student_id, status='Overdue').first()
        if fee:
            score += 20
            reasons.append("Overdue fee payment pending.")

        # 4. Proxy Attendance Check
        proxy_records = AttendanceRecord.query.filter_by(student_id=student_id, is_proxy_suspect=True).count()
        if proxy_records > 0:
            score += 15
            reasons.append(f"Flagged for {proxy_records} potential proxy attendance anomaly.")

        score = min(99.0, max(5.0, round(score, 1)))
        student.risk_score = score
        student.risk_reason = " | ".join(reasons) if reasons else "No major risk factors detected."
        db.session.commit()

        return score, reasons

    @staticmethod
    def detect_proxy_attendance(student_id, subject_id, date_str):
        # Heuristic proxy detector: e.g. student absent in morning & afternoon classes but present in middle class
        records = AttendanceRecord.query.filter_by(student_id=student_id).order_by(AttendanceRecord.date.desc()).limit(5).all()
        absent_count = sum(1 for r in records if r.status == 'absent')
        if absent_count >= 3:
            return True, "Abrupt attendance pattern deviation detected."
        return False, None
