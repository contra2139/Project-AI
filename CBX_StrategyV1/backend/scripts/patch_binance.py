import os
import sys

def patch_binance():
    # Identify the file
    path = r"C:\Users\MSI GF\AppData\Local\Programs\Python\Python313\Lib\site-packages\binance\helpers.py"
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # The bug: return fut without fut defined in async_property
    # Looking at the source, it should be return asyncio.run_coroutine_threadsafe(func(self), loop)
    # or defining fut.
    
    old_code = """        fut = asyncio.run_coroutine_threadsafe(func(self), loop)
        return fut"""
    
    # Wait, if I can't see the exact code, I'll use a safer replacement
    # Based on traceback, it's at line 25.
    
    if "return fut" in content and "fut =" not in content.split("async_property")[1].split("return fut")[0]:
        print("Bug detected. Patching...")
        # Simple fix: replace the problematic return
        new_content = content.replace("return fut", "return asyncio.run_coroutine_threadsafe(func(self), loop)")
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Patch applied successfully.")
    else:
        print("Bug not found or already patched.")

if __name__ == "__main__":
    patch_binance()
