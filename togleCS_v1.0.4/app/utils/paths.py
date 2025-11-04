import os, sys

# 개발자모드와 exe실행파일 모드에서의 경로 설정 유틸리티
def get_data_dir():
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)  # run.exe 위치
        print("💾 exe실행파일로 실행시")
    else:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        print("💾 개발자모드에서 실행시")
    return base_dir
