import argparse

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Role, User
from app.security import hash_password


def create_admin(email: str, password: str) -> None:
    Base.metadata.create_all(engine)
    with SessionLocal.begin() as db:
        user = db.scalar(select(User).where(User.email == email.lower()))
        if user:
            user.password_hash = hash_password(password)
            user.role = Role.SUPER_ADMIN
            user.is_active = True
            print(f"Updated super-admin account: {email}")
        else:
            db.add(User(email=email.lower(), password_hash=hash_password(password), role=Role.SUPER_ADMIN))
            print(f"Created super-admin account: {email}")


def create_worker(email: str, password: str) -> None:
    Base.metadata.create_all(engine)
    with SessionLocal.begin() as db:
        user = db.scalar(select(User).where(User.email == email.lower()))
        if user:
            user.password_hash = hash_password(password)
            user.role = Role.AUTOMATION_WORKER
            user.is_active = True
            print(f"Updated automation worker account: {email}")
        else:
            db.add(User(email=email.lower(), password_hash=hash_password(password), role=Role.AUTOMATION_WORKER))
            print(f"Created automation worker account: {email}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Flight operations administration")
    subparsers = parser.add_subparsers(dest="command", required=True)
    admin = subparsers.add_parser("create-admin", help="Create or reset a super-admin")
    admin.add_argument("--email", required=True)
    admin.add_argument("--password", required=True)
    worker = subparsers.add_parser("create-worker", help="Create or reset an n8n automation worker")
    worker.add_argument("--email", required=True)
    worker.add_argument("--password", required=True)
    args = parser.parse_args()
    if args.command == "create-admin":
        create_admin(args.email, args.password)
    elif args.command == "create-worker":
        create_worker(args.email, args.password)


if __name__ == "__main__":
    main()
