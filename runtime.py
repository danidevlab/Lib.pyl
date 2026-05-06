import re
import os
import sys
import xml.etree.ElementTree as ET
import zipfile
import tempfile
import shutil
import urllib.request
from pathlib import Path

class LibPylRuntime:
    def __init__(self):
        self.libraries = {}
        self.load_certified_libraries()
    
    def load_certified_libraries(self):
        """api/certified_library/librarys.xml에서 인증된 라이브러리 로드"""
        xml_path = "https://github.com/danidevlab/Lib.pyl/blob/27398a34640bcaed78375985a08d5c8a755bd7d1/api/certified_library/librarys.xml"
        
        if not os.path.exists(xml_path):
            print(f"경고: {xml_path}를 찾을 수 없습니다.")
            return
        
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            for library in root.findall(".//library"):
                name_elem = library.find("name")
                file_elem = library.find("libraryfile")
                
                if name_elem is not None and file_elem is not None:
                    lib_name = name_elem.text.strip()
                    lib_file = file_elem.text.strip()
                    self.libraries[lib_name] = lib_file
        except Exception as e:
            print(f"XML 파싱 오류: {e}")
    
    def import_library(self, lib_name):
        """라이브러리 임포트 (인증된 라이브러리 또는 URL)"""
        
        # URL 패턴 체크 (http://, https://, ftp://)
        if lib_name.startswith(('http://', 'https://', 'ftp://')):
            return self.import_from_url(lib_name)
        
        # 인증된 라이브러리 체크
        if lib_name in self.libraries:
            lib_path = self.libraries[lib_name]
            return self.load_pyllib(lib_path)
        
        raise ImportError(f"라이브러리 '{lib_name}'을(를) 찾을 수 없습니다.")
    
    def import_from_url(self, url):
        """URL에서 라이브러리 다운로드 및 임포트"""
        try:
            print(f"다운로드 중: {url}")
            
            # URL이 .pyllib으로 끝나지 않으면 추가
            if not url.endswith('.pyllib'):
                url = url.rstrip('/') + '.pyllib'
            
            # 임시 디렉토리에 다운로드
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pyllib') as tmp:
                urllib.request.urlretrieve(url, tmp.name)
                temp_path = tmp.name
            
            # 다운로드된 파일 로드
            functions = self.load_pyllib(temp_path)
            
            # 임시 파일 삭제
            os.unlink(temp_path)
            
            return functions
        except Exception as e:
            raise ImportError(f"URL '{url}'에서 라이브러리를 가져올 수 없습니다: {e}")
    
    def load_pyllib(self, lib_path):
        """
        .pyllib 파일(zip) 로드
        구조:
        ├── pyfunctions
        │   ├── function1.py
        │   ├── function2.py
        └── info.xml
        """
        if not os.path.exists(lib_path):
            raise FileNotFoundError(f"라이브러리 파일을 찾을 수 없습니다: {lib_path}")
        
        functions = {}
        
        try:
            with zipfile.ZipFile(lib_path, 'r') as zf:
                # pyfunctions 디렉토리의 모든 .py 파일 로드
                for file_info in zf.filelist:
                    if file_info.filename.startswith('pyfunctions/') and file_info.filename.endswith('.py'):
                        func_name = os.path.basename(file_info.filename)[:-3]  # .py 제거
                        code = zf.read(file_info).decode('utf-8')
                        functions[func_name] = code
        except zipfile.BadZipFile:
            raise ImportError(f"유효하지 않은 라이브러리 파일: {lib_path}")
        
        return functions
    
    def execute_function(self, lib_name, func_name, args):
        """라이브러리의 함수 실행"""
        functions = self.import_library(lib_name)
        
        if func_name not in functions:
            raise AttributeError(f"함수 '{func_name}'을(를) '{lib_name}'에서 찾을 수 없습니다.")
        
        # 함수 코드 실행
        code = functions[func_name]
        namespace = {}
        exec(code, namespace)
        
        # 함수 호출
        # 함수명이 첫 번째 정의된 함수라고 가정
        func = None
        for name, obj in namespace.items():
            if callable(obj) and not name.startswith('_'):
                func = obj
                break
        
        if func is None:
            raise RuntimeError(f"'{func_name}'에서 실행 가능한 함수를 찾을 수 없습니다.")
        
        try:
            result = func(args)
            return result
        except Exception as e:
            raise RuntimeError(f"함수 실행 오류: {e}")
    
    def parse_and_execute(self, code):
        """Lib.pyl 코드 파싱 및 실행"""
        lines = code.strip().split('\n')
        
        for line in lines:
            # 주석 제거 (^...^)
            line = re.sub(r'\^.*?\^', '', line).strip()
            
            if not line or line == 'end':
                continue
            
            # import"libname" 패턴
            import_match = re.match(r'import"([^"]+)"', line)
            if import_match:
                lib_name = import_match.group(1)
                self.import_library(lib_name)
                print(f"✓ 라이브러리 임포트: {lib_name}")
                continue
            
            # "libname"_"funcname"_"args" 패턴
            call_match = re.match(r'"([^"]+)"_"([^"]+)"_"([^"]*)"', line)
            if call_match:
                lib_name = call_match.group(1)
                func_name = call_match.group(2)
                args = call_match.group(3)
                
                try:
                    result = self.execute_function(lib_name, func_name, args)
                    print(f"결과: {result}")
                except Exception as e:
                    print(f"오류: {e}")
                continue


def main():
    if len(sys.argv) < 2:
        print("사용법: python runtime.py <파일명.pyl>")
        sys.exit(1)
    
    pyl_file = sys.argv[1]
    
    if not os.path.exists(pyl_file):
        print(f"오류: 파일을 찾을 수 없습니다: {pyl_file}")
        sys.exit(1)
    
    with open(pyl_file, 'r', encoding='utf-8') as f:
        code = f.read()
    
    runtime = LibPylRuntime()
    runtime.parse_and_execute(code)


if __name__ == "__main__":
    main()
