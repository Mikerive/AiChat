from setuptools import setup, find_packages
from pathlib import Path

def read_requirements():
    # Attempt to read requirements from the repository root (two levels up)
    req_path = Path(__file__).parents[2] / "requirements.txt"
    if req_path.exists():
        return [
            line.strip() for line in req_path.read_text().splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
    return []

setup(
    name="vtuber-chat-app",
    version="0.1.0",
    description="VTuber chat backend API (chat_app)",
    packages=find_packages(),
    include_package_data=True,
    install_requires=read_requirements(),
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)