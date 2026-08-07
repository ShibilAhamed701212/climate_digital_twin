# Contributing to Climate Digital Twin

Thank you for your interest in contributing to the **Climate Digital Twin** project! We welcome contributions from developers, climate scientists, data engineers, and open-source enthusiasts.

---

## Code of Conduct

This project adheres to our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

---

## How to Contribute

### 1. Reporting Bugs
- Check existing issues in GitHub Issues before submitting a new report.
- Use the **Bug Report** issue template.
- Include OS details, Python version, steps to reproduce, and relevant logs.

### 2. Requesting Features
- Use the **Feature Request** issue template.
- Explain the user benefit, technical design, and potential integration points.

### 3. Submitting Pull Requests
1. Fork the repository and create a feature branch (`git checkout -b feature/my-feature`).
2. Follow PEP8 style guidelines and format code with `ruff format .`.
3. Ensure all tests pass (`make test` or `pytest`).
4. Ensure zero linter errors (`make lint` or `ruff check .`).
5. Keep commits atomic and write clear commit messages.
6. Open a Pull Request referencing your issue.

---

## Local Development Setup

```bash
# Clone the repository
git clone https://github.com/ShibilAhamed701212/climate_digital_twin.git
cd climate_digital_twin

# Create virtual environment & install dependencies
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Download sample dataset
make download-data

# Run linter and tests
make lint
make test
```

---

## License

By contributing, you agree that your contributions will be licensed under the project's [Apache 2.0 / MIT License](LICENSE).
