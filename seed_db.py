import os
from datetime import datetime, timedelta
from app import app, db
from app.models import User, Problem, StudyGroup, StudyGroupMember, Contest, ContestProblem, ContestTestCase

def seed_database():
    print("Seeding database...")
    
    # 1. Create Admin User
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(
            username="admin",
            email="admin@codementor.ai",
            role="admin",
            first_name="CodeMentor",
            last_name="Administrator",
            bio="System Administrator for CodeMentor AI"
        )
        admin.set_password("admin123")
        db.session.add(admin)
        print("Created Admin user: admin / admin123")
    else:
        print("Admin user already exists")
        
    # 2. Create Student User
    student = User.query.filter_by(username="student").first()
    if not student:
        student = User(
            username="student",
            email="student@codementor.ai",
            role="student",
            first_name="Alex",
            last_name="Coder",
            bio="Aspiring Software Engineer",
            learning_goals="Master Python, Data Structures, and Algorithms",
            target_companies="Google, Microsoft, Meta"
        )
        student.set_password("student123")
        db.session.add(student)
        print("Created Student user: student / student123")
    else:
        print("Student user already exists")
        
    db.session.commit()
    
    # Re-query users to get IDs
    admin = User.query.filter_by(username="admin").first()
    student = User.query.filter_by(username="student").first()
    
    # 3. Create Sample Problems
    if Problem.query.count() == 0:
        problems = [
            Problem(
                title="Two Sum",
                platform="leetcode",
                difficulty="Easy",
                category="Arrays",
                url="https://leetcode.com/problems/two-sum",
                description="Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target."
            ),
            Problem(
                title="Reverse String",
                platform="leetcode",
                difficulty="Easy",
                category="Strings",
                url="https://leetcode.com/problems/reverse-string",
                description="Write a function that reverses a string. The input string is given as an array of characters s."
            ),
            Problem(
                title="Merge Intervals",
                platform="leetcode",
                difficulty="Medium",
                category="Arrays",
                url="https://leetcode.com/problems/merge-intervals",
                description="Given an array of intervals where intervals[i] = [starti, endi], merge all overlapping intervals."
            )
        ]
        db.session.add_all(problems)
        print("Added sample problems")
        
    # 4. Create Sample Study Group
    if StudyGroup.query.count() == 0:
        group = StudyGroup(
            name="Python Masterminds",
            description="A group for intermediate Python developers to practice algorithms together and crack coding interviews.",
            topic="Algorithms",
            skill_level="Intermediate",
            max_members=10,
            created_by=student.id
        )
        db.session.add(group)
        db.session.flush()
        
        # Add creator as moderator member
        member = StudyGroupMember(
            group_id=group.id,
            user_id=student.id,
            role="moderator"
        )
        db.session.add(member)
        print("Created study group: Python Masterminds")
        
    # 5. Create Sample Contest
    if Contest.query.count() == 0:
        # Create a live contest starting now
        contest = Contest(
            title="Weekly Code Challenge #1",
            description="Solve basic algorithms problems and compete with your peers!",
            start_date=datetime.now() - timedelta(minutes=10),
            duration_minutes=120,
            created_by=admin.id
        )
        db.session.add(contest)
        db.session.flush()
        
        # Add a contest problem
        problem = ContestProblem(
            contest_id=contest.id,
            title="Sum of Two Numbers",
            description="Write a function named `solution(a, b)` that returns the sum of two integers `a` and `b`.",
            constraints="a and b are integers between -10^9 and 10^9.",
            examples="Input: a = 2, b = 3\nOutput: 5",
            points=100
        )
        db.session.add(problem)
        db.session.flush()
        
        # Add test cases
        tc1 = ContestTestCase(
            problem_id=problem.id,
            input_data="5 7",
            expected_output="12",
            is_sample=True
        )
        tc2 = ContestTestCase(
            problem_id=problem.id,
            input_data="-3 8",
            expected_output="5",
            is_sample=False
        )
        db.session.add_all([tc1, tc2])
        print("Created contest: Weekly Code Challenge #1 with sample problem and test cases")
        
    db.session.commit()
    print("Database seeding complete!")

if __name__ == "__main__":
    with app.app_context():
        seed_database()
