#!/usr/bin/env python3
"""
Setup configuration for Faust Math Teacher Terminal Application
"""

from setuptools import setup, find_packages

# Read requirements from requirements.txt
def read_requirements():
    with open('requirements.txt', 'r') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

# Read long description from README
def read_readme():
    try:
        with open('README.md', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Faust - AI Math Teacher Terminal Application"

setup(
    name="faust-math",
    version="2.0.0",
    author="Faust Developer",
    author_email="dev@faust-math.ai",
    description="Faust - A brilliant but emotionally distant AI math tutor in your terminal",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/faust-math",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "Topic :: Education :: Computer Aided Instruction (CAI)",
        "Topic :: Scientific/Engineering :: Mathematics",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Environment :: Console",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    entry_points={
        "console_scripts": [
            "faust=faust.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "faust": ["*.txt", "*.md"],
    },
    keywords="math education ai teacher terminal cli gemini",
    project_urls={
        "Bug Reports": "https://github.com/your-username/faust-math/issues",
        "Source": "https://github.com/your-username/faust-math",
    },
)