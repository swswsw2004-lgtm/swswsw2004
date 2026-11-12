"""파일 저장소 테스트. 담당: 팀원2"""
import pytest

from pacs.storage import LocalStorage, StorageError


def test_save_read_delete(tmp_path):
    s = LocalStorage(tmp_path)
    p1 = s.save(b"abc", "originals/MOCK-1", "png")
    p2 = s.save(b"abc", "originals/MOCK-1", ".png")
    assert p1 != p2, "같은 내용이어도 덮어쓰지 않고 새 파일로 저장"
    assert s.read(p1) == b"abc"
    s.delete(p1)
    assert not s.exists(p1)


def test_path_traversal_blocked(tmp_path):
    with pytest.raises(StorageError):
        LocalStorage(tmp_path / "store").read("../../etc/passwd")
