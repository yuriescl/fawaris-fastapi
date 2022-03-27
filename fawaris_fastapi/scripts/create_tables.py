import sqlalchemy
import typer
from fawaris_fastapi.tables import metadata
from fawaris_fastapi import settings

def main():
    engine = sqlalchemy.create_engine(
        settings.DATABASE_URL, connect_args={"check_same_thread": False}
    )
    metadata.create_all(engine)


if __name__ == "__main__":
    typer.run(main)
