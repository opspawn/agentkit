import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

# Import the class to test
from agentkit.tools.llm_tool import GenericLLMTool

# Mock the ModelResponse structure from litellm if needed for assertions
# This avoids a direct dependency on litellm just for test mocks if possible,
# but sometimes importing the real structure helps. For now, use MagicMock.
MockModelResponse = MagicMock()
# Example structure:
# MockModelResponse.choices = [MagicMock(message=MagicMock(content="Test response"))]
# MockModelResponse.dict.return_value = {
#     "id": "cmpl-mockid",
#     "choices": [{"finish_reason": "stop", "index": 0, "message": {"content": "Test response", "role": "assistant"}}],
#     "created": 1700000000,
#     "model": "gpt-3.5-turbo",
#     "object": "chat.completion",
#     "system_fingerprint": None,
#     "usage": {"completion_tokens": 5, "prompt_tokens": 10, "total_tokens": 15}
# }


@pytest.fixture
def llm_tool():
    """Fixture to provide an instance of GenericLLMTool."""
    # Patch load_dotenv during instantiation for all tests using this fixture
    with patch('agentkit.tools.llm_tool.load_dotenv') as mock_load_dotenv:
        tool = GenericLLMTool()
        mock_load_dotenv.assert_called_once() # Ensure it was called during init
        return tool

# --- Test Cases ---

def test_get_definition(llm_tool):
    """Verify the structure and content of the tool definition."""
    definition = llm_tool.get_definition()

    assert isinstance(definition, dict)
    assert definition["name"] == "generic_llm_completion"
    assert "description" in definition
    assert "parameters" in definition
    assert definition["parameters"]["type"] == "object"
    assert "model" in definition["parameters"]["properties"]
    assert "messages" in definition["parameters"]["properties"]
    assert "temperature" in definition["parameters"]["properties"] # Check one optional param
    assert "model" in definition["parameters"]["required"]
    assert "messages" in definition["parameters"]["required"]

@pytest.mark.asyncio
@patch('agentkit.tools.llm_tool.litellm.acompletion', new_callable=AsyncMock)
async def test_execute_success(mock_acompletion, llm_tool):
    """Test successful execution path."""
    # Configure the mock response
    mock_response_instance = MockModelResponse()
    mock_response_instance.dict.return_value = {
        "id": "cmpl-mocksuccess", "choices": [{"message": {"content": "Success!"}}], "model": "test-model"
    }
    mock_acompletion.return_value = mock_response_instance

    params = {
        "model": "test-model",
        "messages": [{"role": "user", "content": "Hello"}],
        "temperature": 0.5 # Include an optional param
    }
    result = await llm_tool.execute(parameters=params)

    assert result["status"] == "success"
    assert "result" in result
    assert result["result"]["id"] == "cmpl-mocksuccess"
    assert result["result"]["choices"][0]["message"]["content"] == "Success!"

    # Verify acompletion was called correctly
    mock_acompletion.assert_awaited_once_with(
        model="test-model",
        messages=[{"role": "user", "content": "Hello"}],
        temperature=0.5
    )

@pytest.mark.asyncio
async def test_execute_missing_required_params(llm_tool):
    """Test execution when required parameters are missing."""
    params_missing_model = {
        "messages": [{"role": "user", "content": "Hello"}]
    }
    result_model = await llm_tool.execute(parameters=params_missing_model)
    assert result_model["status"] == "error"
    assert "Missing required parameters" in result_model["error_message"]

    params_missing_messages = {
        "model": "test-model"
    }
    result_messages = await llm_tool.execute(parameters=params_missing_messages)
    assert result_messages["status"] == "error"
    assert "Missing required parameters" in result_messages["error_message"]

@pytest.mark.asyncio
@patch('agentkit.tools.llm_tool.litellm.acompletion', new_callable=AsyncMock)
async def test_execute_litellm_exception(mock_acompletion, llm_tool):
    """Test execution when litellm.acompletion raises an exception."""
    # Configure the mock to raise an error
    mock_acompletion.side_effect = Exception("LiteLLM API Error")

    params = {
        "model": "test-model",
        "messages": [{"role": "user", "content": "Hello"}]
    }
    result = await llm_tool.execute(parameters=params)

    assert result["status"] == "error"
    assert "LLM execution failed" in result["error_message"]
    assert "Exception: LiteLLM API Error" in result["error_message"]
    mock_acompletion.assert_awaited_once() # Ensure it was called

@pytest.mark.asyncio
@patch('agentkit.tools.llm_tool.litellm.acompletion', new_callable=AsyncMock)
async def test_execute_optional_params_passed(mock_acompletion, llm_tool):
    """Test that optional parameters are correctly passed to acompletion."""
    mock_response_instance = MockModelResponse()
    mock_response_instance.dict.return_value = {"id": "cmpl-mockoptional", "choices": [{"message": {"content": "Optional!"}}]}
    mock_acompletion.return_value = mock_response_instance

    params = {
        "model": "test-model",
        "messages": [{"role": "user", "content": "Optional test"}],
        "max_tokens": 100,
        "temperature": 0.9,
        "top_p": 0.8,
        "stream": False, # Explicitly false
        "stop": ["\n"],
        "presence_penalty": 0.1,
        "frequency_penalty": -0.1
    }
    result = await llm_tool.execute(parameters=params)

    assert result["status"] == "success"
    mock_acompletion.assert_awaited_once_with(
        model="test-model",
        messages=[{"role": "user", "content": "Optional test"}],
        max_tokens=100,
        temperature=0.9,
        top_p=0.8,
        stream=False,
        stop=["\n"],
        presence_penalty=0.1,
        frequency_penalty=-0.1
    )

# Test that load_dotenv is called on init (covered by fixture)
def test_init_loads_dotenv(llm_tool):
     """This test primarily relies on the fixture setup to assert load_dotenv was called."""
     # The assertion is in the fixture itself
     assert llm_tool is not None # Basic check that fixture worked