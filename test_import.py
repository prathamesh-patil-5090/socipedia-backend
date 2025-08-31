import sys
import os

# Add the path to your combined_model directory
combined_model_path = os.path.join(os.path.dirname(__file__), 'combined_model', 'combined_model')
print(f"Looking for model at: {combined_model_path}")
print(f"Path exists: {os.path.exists(combined_model_path)}")

sys.path.append(combined_model_path)

try:
    import infer
    print("Import successful!")
    
    # Test the function
    result = infer.should_block_content("u fucker")
    print(f"Test result: {result}")
    
except ImportError as e:
    print(f"Import failed: {e}")
except Exception as e:
    print(f"Other error: {e}")
