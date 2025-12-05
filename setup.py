"""Setup configuration for Dubplate Authenticator."""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="dubplate-authenticator",
    version="1.0.0",
    author="Dubplate Authenticator Team",
    author_email="info@dubplate-auth.com",
    description="Authenticate and verify dubplates for sound clash culture",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jnrmello247-png/Dubplate-Authenticator-",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "dubplate-auth=dubplate_auth.cli:main",
        ],
    },
)
