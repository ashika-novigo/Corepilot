from db.database import SessionLocal
from models.employee import Employee


def seed_employees():
    db = SessionLocal()

    users = [
        {
            "name": "Ashika",
            "email": "employee@novigo.com",
            "role": "employee",
            "department": "General",
        },
        {
            "name": "Maya",
            "email": "manager@novigo.com",
            "role": "manager",
            "department": "Operations",
        },
        {
            "name": "Hari",
            "email": "hr@novigo.com",
            "role": "hr",
            "department": "HR",
        },
        {
            "name": "Iran",
            "email": "it@novigo.com",
            "role": "it",
            "department": "IT",
        },
        {
            "name": "Fince",
            "email": "finance@novigo.com",
            "role": "finance",
            "department": "Finance",
        },
        {
            "name": "Admin",
            "email": "admin@novigo.com",
            "role": "admin",
            "department": "Admin",
        },
    ]

    for user in users:
        existing = db.query(Employee).filter(Employee.email == user["email"]).first()

        if not existing:
            db.add(Employee(**user))

    db.commit()
    db.close()

    print("Employees seeded successfully.")


if __name__ == "__main__":
    seed_employees()