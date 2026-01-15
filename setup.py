"""Setup configuration for market_risk_os."""

from setuptools import setup, find_packages

setup(
    name="market_risk_os",
    version="0.1.0",
    description="A comprehensive market risk analysis system",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
        ],
    },
)


