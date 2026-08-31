"""
Unit tests untuk core.state module.

Test coverage:
- State creation dan deletion
- State updates
- WorkflowState wrapper
- State isolation antara state_ids
"""
import pytest

from core.state import WorkflowState, delete_state, get_state, new_state_id


@pytest.mark.unit
class TestCoreState:
    """Test suite untuk core.state"""

    def test_get_default_state(self, clean_state):
        """Test default state structure."""
        state = get_state()
        assert state is not None
        assert isinstance(state, dict)
        assert "target_column" in state
        assert state["target_column"] is None

    def test_get_state_with_custom_id(self, clean_state):
        """Test getting state dengan custom state_id."""
        state_id = new_state_id()
        state = get_state(state_id)
        assert state is not None
        assert isinstance(state, dict)

    def test_new_state_id_generates_unique_ids(self, clean_state):
        """Test new_state_id() generates unique IDs."""
        id1 = new_state_id()
        id2 = new_state_id()
        id3 = new_state_id()
        assert id1 != id2
        assert id2 != id3
        assert id1 != id3

    def test_set_and_get_state_value(self, clean_state):
        """Test setting dan getting value dalam state."""
        state_id = new_state_id()
        state = get_state(state_id)
        state["target_column"] = "churn"
        
        # Retrieve kembali
        retrieved_state = get_state(state_id)
        assert retrieved_state["target_column"] == "churn"

    def test_delete_state(self, clean_state):
        """Test state deletion."""
        state_id = new_state_id()
        state = get_state(state_id)
        state["target_column"] = "churn"
        
        # Verify set
        assert get_state(state_id)["target_column"] == "churn"
        
        # Delete
        delete_state(state_id)
        
        # Verify deleted (should return fresh state)
        new_state = get_state(state_id)
        assert new_state["target_column"] is None

    def test_state_isolation_between_ids(self, clean_state):
        """Test states dengan different IDs tidak mempengaruhi satu sama lain."""
        id1 = new_state_id()
        id2 = new_state_id()
        
        state1 = get_state(id1)
        state2 = get_state(id2)
        
        state1["target_column"] = "churn"
        state2["target_column"] = "salary"
        
        # Verify isolation
        assert get_state(id1)["target_column"] == "churn"
        assert get_state(id2)["target_column"] == "salary"

    def test_workflow_state_wrapper_basic(self, clean_state):
        """Test WorkflowState wrapper initialization."""
        state_id = new_state_id()
        ws = WorkflowState(state_id)
        assert ws is not None

    def test_workflow_state_dict_like_access(self, clean_state):
        """Test WorkflowState supports dict-like access."""
        state_id = new_state_id()
        ws = WorkflowState(state_id)
        
        ws["problem_type"] = "Classification"
        assert ws["problem_type"] == "Classification"

    def test_workflow_state_set_method(self, clean_state):
        """Test WorkflowState.set() method."""
        state_id = new_state_id()
        ws = WorkflowState(state_id)
        
        ws.set(target_column="y", problem_type="Classification")
        assert ws["target_column"] == "y"
        assert ws["problem_type"] == "Classification"

    def test_workflow_state_get_method(self, clean_state):
        """Test WorkflowState.get() method with default."""
        state_id = new_state_id()
        ws = WorkflowState(state_id)
        
        # Get non-existent key dengan default
        result = ws.get("non_existent", "default_value")
        assert result == "default_value"

    def test_workflow_state_update_existing_keys(self, clean_state):
        """Test updating existing keys dalam WorkflowState."""
        state_id = new_state_id()
        ws = WorkflowState(state_id)
        
        ws.set(n_samples=100)
        assert ws["n_samples"] == 100
        
        ws.set(n_samples=200)
        assert ws["n_samples"] == 200

    def test_workflow_state_persistence(self, clean_state):
        """Test WorkflowState changes persist in underlying state."""
        state_id = new_state_id()
        ws = WorkflowState(state_id)
        
        ws.set(target_column="y")
        
        # Access via get_state directly
        state = get_state(state_id)
        assert state["target_column"] == "y"

    def test_multiple_workflow_state_wrappers_same_id(self, clean_state):
        """Test multiple WorkflowState wrappers untuk same ID."""
        state_id = new_state_id()
        ws1 = WorkflowState(state_id)
        ws2 = WorkflowState(state_id)
        
        ws1.set(value=100)
        # ws2 should see changes dari ws1
        assert ws2.get("value") == 100

    def test_state_with_various_data_types(self, clean_state):
        """Test state dapat menyimpan berbagai tipe data."""
        state_id = new_state_id()
        state = get_state(state_id)
        
        state["string_val"] = "test"
        state["int_val"] = 42
        state["float_val"] = 3.14
        state["bool_val"] = True
        state["list_val"] = [1, 2, 3]
        state["dict_val"] = {"key": "value"}
        
        retrieved = get_state(state_id)
        assert retrieved["string_val"] == "test"
        assert retrieved["int_val"] == 42
        assert retrieved["float_val"] == 3.14
        assert retrieved["bool_val"] is True
        assert retrieved["list_val"] == [1, 2, 3]
        assert retrieved["dict_val"] == {"key": "value"}

    def test_state_none_value_handling(self, clean_state):
        """Test state handles None values correctly."""
        state_id = new_state_id()
        state = get_state(state_id)
        
        state["optional_val"] = None
        retrieved = get_state(state_id)
        assert retrieved["optional_val"] is None

    def test_default_state_has_required_keys(self, clean_state):
        """Test default state has expected keys."""
        state = get_state()
        required_keys = ["target_column", "numerical_columns", "categorical_columns", "problem_type"]
        for key in required_keys:
            assert key in state, f"Required key '{key}' not in default state"

    def test_workflow_state_with_none_state_id(self, clean_state):
        """Test WorkflowState dengan None state_id uses default."""
        ws = WorkflowState(None)
        ws.set(test_key="test_value")
        # Should work (uses default state)
        assert ws.get("test_key") == "test_value"
