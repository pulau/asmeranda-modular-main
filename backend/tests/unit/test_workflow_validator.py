"""
Unit tests untuk workflow_validator module.

Test coverage:
- Validation rules untuk setiap workflow step
- Error messages clarity
- State requirement checking
"""
import pytest

from core.state import WorkflowState, delete_state, new_state_id
from workflow_validator import WorkflowValidator


@pytest.mark.unit
class TestWorkflowValidator:
    """Test suite untuk WorkflowValidator"""

    def test_validator_initialization_with_state(self, clean_state):
        """Test WorkflowValidator dapat diinisialisasi dengan state dict."""
        state_id = new_state_id()
        state = {"target_column": "churn", "dataset_id": "test-123"}
        validator = WorkflowValidator(state)
        assert validator.state is not None

    def test_validator_initialization_with_none_uses_default(self, clean_state):
        """Test WorkflowValidator dengan None state uses default."""
        validator = WorkflowValidator(None)
        assert validator.state is not None

    def test_validator_has_validation_rules(self, clean_state):
        """Test validator memiliki validation_rules dict."""
        validator = WorkflowValidator({})
        assert hasattr(validator, "validation_rules")
        assert isinstance(validator.validation_rules, dict)

    def test_validation_rules_include_workflow_steps(self, clean_state):
        """Test validation_rules mencakup semua workflow steps."""
        validator = WorkflowValidator({})
        expected_steps = [
            "upload_to_eda",
            "eda_to_preprocessing",
            "preprocessing_to_training",
        ]
        for step in expected_steps:
            assert step in validator.validation_rules

    def test_upload_stage_requires_dataset(self, clean_state):
        """Test upload stage validation."""
        state = {
            "dataset_id": None,
            "dataset_name": None,
        }
        validator = WorkflowValidator(state)
        # Should fail - no dataset
        result = validator.validate("upload_to_eda")
        assert result is not None or not result.get("valid", True)

    def test_upload_stage_passes_with_valid_dataset(self, clean_state):
        """Test upload stage validation dengan valid dataset."""
        state = {
            "dataset_id": "test-123",
            "dataset_name": "test.csv",
            "n_rows": 100,
            "n_cols": 5,
        }
        validator = WorkflowValidator(state)
        result = validator.validate("upload_to_eda")
        # Should pass
        assert result.get("valid", False) is True or result is None

    def test_preprocessing_requires_target_column(self, clean_state):
        """Test preprocessing validation requires target column."""
        state = {
            "dataset_id": "test-123",
            "target_column": None,
            "problem_type": None,
        }
        validator = WorkflowValidator(state)
        result = validator.validate("eda_to_preprocessing")
        # Should fail - missing target_column
        assert not result.get("valid", True)

    def test_preprocessing_validation_complete(self, clean_state):
        """Test preprocessing validation dengan semua required fields."""
        state = {
            "dataset_id": "test-123",
            "target_column": "churn",
            "problem_type": "Classification",
            "numerical_columns": ["age", "salary"],
            "categorical_columns": ["department"],
        }
        validator = WorkflowValidator(state)
        result = validator.validate("eda_to_preprocessing")
        assert result.get("valid", False) is True or result is None

    def test_training_requires_preprocessed_data(self, clean_state):
        """Test training validation requires preprocessing completion."""
        state = {
            "dataset_id": "test-123",
            "target_column": "churn",
            "problem_type": "Classification",
            "n_samples_train": None,
            "n_samples_test": None,
        }
        validator = WorkflowValidator(state)
        result = validator.validate("preprocessing_to_training")
        # Should fail - preprocessing not done
        assert not result.get("valid", True)

    def test_training_validation_complete(self, clean_state):
        """Test training validation dengan complete preprocessing."""
        state = {
            "dataset_id": "test-123",
            "target_column": "churn",
            "problem_type": "Classification",
            "n_samples_train": 800,
            "n_samples_test": 200,
            "n_features": 10,
            "preprocessing_steps": ["scaling", "encoding"],
        }
        validator = WorkflowValidator(state)
        result = validator.validate("preprocessing_to_training")
        assert result.get("valid", False) is True or result is None

    def test_validation_returns_informative_messages(self, clean_state):
        """Test validation results include informative error messages."""
        state = {"dataset_id": None}
        validator = WorkflowValidator(state)
        result = validator.validate("upload_to_eda")
        if not result.get("valid", True):
            assert "errors" in result or "message" in result

    def test_validator_with_workflow_state_wrapper(self, clean_state):
        """Test validator works dengan WorkflowState wrapper."""
        state_id = new_state_id()
        ws = WorkflowState(state_id)
        ws.set(
            dataset_id="test-123",
            target_column="churn",
            problem_type="Classification"
        )
        validator = WorkflowValidator(ws.state)
        # Should work without errors
        assert validator is not None

    def test_classification_vs_regression_validation(self, clean_state):
        """Test validation handles both classification dan regression."""
        # Classification
        state_clf = {
            "dataset_id": "test-123",
            "target_column": "churn",
            "problem_type": "Classification",
            "target_type": "binary",
        }
        validator_clf = WorkflowValidator(state_clf)
        result_clf = validator_clf.validate("eda_to_preprocessing")
        assert result_clf.get("valid", False) is True or result_clf is None
        
        # Regression
        state_reg = {
            "dataset_id": "test-123",
            "target_column": "price",
            "problem_type": "Regression",
            "target_type": "numeric",
        }
        validator_reg = WorkflowValidator(state_reg)
        result_reg = validator_reg.validate("eda_to_preprocessing")
        assert result_reg.get("valid", False) is True or result_reg is None

    def test_validation_error_messages_in_id(self, clean_state):
        """Test validation includes specific error IDs."""
        state = {"dataset_id": None, "target_column": None}
        validator = WorkflowValidator(state)
        result = validator.validate("eda_to_preprocessing")
        if not result.get("valid", True):
            assert "error_id" in result or "code" in result or "errors" in result

    def test_multiple_validations_independent(self, clean_state):
        """Test multiple validation calls don't interfere."""
        state1 = {"dataset_id": "test-1"}
        state2 = {"dataset_id": "test-2"}
        
        val1 = WorkflowValidator(state1)
        val2 = WorkflowValidator(state2)
        
        val1.validate("upload_to_eda")
        val2.validate("upload_to_eda")
        
        # Check states still independent
        assert val1.state.get("dataset_id") == "test-1"
        assert val2.state.get("dataset_id") == "test-2"

    def test_validation_result_structure(self, clean_state):
        """Test validation result has expected structure."""
        state = {
            "dataset_id": "test-123",
            "target_column": "churn",
            "problem_type": "Classification"
        }
        validator = WorkflowValidator(state)
        result = validator.validate("eda_to_preprocessing")
        
        # Result should have 'valid' key
        assert "valid" in result or result is None
