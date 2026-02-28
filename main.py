import pytest
def main():
    exit_code = pytest.main([])

    if exit_code == 0:
        print("✅ 所有测试用例执行通过！")
    else:
        print("❌ 部分测试用例执行失败/出错！")

if __name__ == "__main__":
    loop_count = 0
    while True:
        if loop_count > 1:
            break
        main()
        loop_count += 1