from pathlib import Path


def test_example_file_exists():
    """Test that the expected output file exists."""
    output_path = Path("/app/output.txt")

    assert output_path.exists(), f"File {output_path} does not exist"


def test_example_file_content():
    """Test that the output file contains the expected content."""
    output_path = Path("/app/output.txt")

    assert output_path.read_text().strip() == "harbor-hell: task completed", (
        f"Expected 'harbor-hell: task completed' but got '{output_path.read_text().strip()}'"
    )
