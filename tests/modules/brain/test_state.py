from pathlib import Path

from app.modules.brain.state import BrainState, StateStore


def test_missing_file_is_a_fresh_state(tmp_path: Path) -> None:
    assert StateStore(tmp_path / "state.json").load() == BrainState()


def test_saved_state_is_loaded_back(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "nested" / "state.json")

    store.save(BrainState(session_id="abc", turns=7))

    assert store.load() == BrainState(session_id="abc", turns=7)
    assert not (tmp_path / "nested" / "state.tmp").exists()


def test_unreadable_file_is_a_fresh_state(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("{not json")

    assert StateStore(path).load() == BrainState()
