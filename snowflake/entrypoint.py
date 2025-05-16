import subprocess


def main():
    subprocess.run(["uvicorn", "snowflake.app:app"])
