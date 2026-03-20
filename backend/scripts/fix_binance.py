import os

def fix_binance():
    base_path = r"e:\Agent_AI_Antigravity\CBX_StrategyV1\backend\.venv\Lib\site-packages\binance"
    if not os.path.exists(base_path):
        print(f"Path not found: {base_path}")
        return

    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    if "async_client" in content:
                        print(f"Fixing {file_path}...")
                        new_content = content.replace("async_client", "a_client")
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                except Exception as e:
                    print(f"Could not fix {file_path}: {e}")

if __name__ == "__main__":
    fix_binance()
