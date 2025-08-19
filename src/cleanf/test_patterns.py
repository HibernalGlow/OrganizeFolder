import re
from config import DELETE_PATTERNS

test_names = [
    "test.bak", "temp_123", "my.trash", "[#hb]hello.txt", "[xx]abc.txt", "normal.txt", "temp_folder", "abc.bak", "temp_file.txt"
]

def test_patterns():
    for name in test_names:
        print(f"\n测试名称: {name}")
        for rule in DELETE_PATTERNS:
            if re.fullmatch(rule["pattern"], name, re.IGNORECASE):
                print(f"  匹配: {rule['pattern']} ({rule['description']}) 类型: {rule['type']}")
            else:
                print(f"  不匹配: {rule['pattern']} ({rule['description']})")

if __name__ == "__main__":
    test_patterns() 