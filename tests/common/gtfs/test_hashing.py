import pytest

from app.importer.hashing import sha256_file


class TestSha256File:
    @pytest.mark.parametrize(
        "content, expected_hash",
        [
            (b"", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
            (b"elo elo 320 ", "01b10497dbbe4dc2c7990b189a98f4fba640ae4a82fcd515b305d5ec0dd88588"),
        ],
    )
    def test_known_hashes(self, tmp_path, content, expected_hash):
        p = tmp_path / "test_file.txt"
        p.write_bytes(content)

        assert sha256_file(p) == expected_hash

    def test_accepts_str_and_path(self, tmp_path):
        p = tmp_path / "input_test.txt"
        p.write_bytes(b"test")

        assert sha256_file(p) == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
        assert sha256_file(str(p)) == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"

    def test_same_content_same_hash(self, tmp_path):
        f1 = tmp_path / "file1.bin"
        f2 = tmp_path / "file2.bin"

        content = b"bardzo wazne dane"
        f1.write_bytes(content)
        f2.write_bytes(content)

        assert sha256_file(f1) == sha256_file(f2)

    def test_different_content_different_hash(self, tmp_path):
        f1 = tmp_path / "file1.bin"
        f2 = tmp_path / "file2.bin"

        f1.write_bytes(b"content A")
        f2.write_bytes(b"content B")

        assert sha256_file(f1) != sha256_file(f2)
