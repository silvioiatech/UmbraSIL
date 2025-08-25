from setuptools import setup, find_packages

setup(
    name="umbrasil",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.104.1",
        "uvicorn[standard]>=0.24.0",
        "python-telegram-bot>=20.7",
        "asyncpg>=0.29.0",
        "python-dotenv>=1.0.0",
    ],
    author="silvioiatech",
    author_email="your.email@example.com",
    description="Personal Telegram Bot Assistant",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.11",
)
