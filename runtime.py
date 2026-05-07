import re
import os
import sys
import xml.etree.ElementTree as ET
import zipfile
import tempfile
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

class LibPylRuntime:
    def __init__(self) -> None:
        self.libraries: Dict[str, str] = {}
        self.imported_functions: Dict[str, Dict[str, str]] = {}
        self.load_certified_libraries()
    
    def load_certified_libraries(self) -> None:
        """api/certified_library/librarys.xml에서 인증된 라이브러리 목록을 로드합니다."""
        # 코딩 똑똑이의 수정: GitHub 일반 URL이 아닌 Raw Data URL을 사용해야 XML을 정상적으로 다운로드할 수 있습니다.
        xml_url = "https://raw.githubusercontent.com/danidevlab/Lib.pyl/27398a34640bcaed78375985a08d5c8a755bd7d1/api/certified_library/librarys.xml"
        
        try:
            req = urllib.request.Request(xml_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                xml_data = response.read()
                
            tree = ET.ElementTree(ET.fromstring(xml_data))
            root = tree.getroot()
            
            for library in root.findall(".//library"):
                name_elem = library.find("name")
                file_elem = library.find("libraryfile")
                
                if name_elem is not None and file_elem is not None:
                    lib_name = name_elem.text.strip() if name_elem.text else ""
                    lib_file = file_elem.text.strip() if file_elem.text else ""
                    if lib_name and lib_file:
                        self.libraries[lib_name] = lib_file
            print(f"✓ 인증된 라이브러리 {len(self.libraries)}개를 성공적으로 로드했습니다.")
            
        except urllib.error.URLError as e:
            print(f"⚠ 경고: 라이브러리 목록을 가져올 수 없습니다. 네트워크를 확인하세요. ({e})")
        except ET.ParseError as e:
            print(f"⚠ 경고: 인증된 라이브러리 XML 파싱 오류 발생: {e}")
        except Exception as e:
            print(f"⚠ 경고: 라이브러리 로드 중 알 수 없는 오류 발생: {e}")
    
    def import_library(self, lib_name: str) -> Dict[str, str]:
        """라이브러리를 임포트하여 함수 목록을 반환합니다. (이미 임포트된 경우 캐시 사용)"""
        if lib_name in self.imported_functions:
            return self.imported_functions[lib_name]

        functions = {}
        
        # URL 패턴 체크 (http://, https://, ftp://)
        if lib_name.startswith(('http://', 'https://', 'ftp://')):
            functions = self.import_from_url(lib_name)
        # 인증된 라이브러리 체크
        elif lib_name in self.libraries:
            lib_path = self.libraries[lib_name]
            # 인증된 라이브러리가 URL 형식인 경우
            if lib_path.startswith(('http://', 'https://')):
                 functions = self.import_from_url(lib_path)
            else:
                 functions = self.load_pyllib(lib_path)
        else:
            # 로컬 파일 경로인 경우 체크
            local_path = f"{lib_name}.pyllib"
            if os.path.exists(local_path):
                functions = self.load_pyllib(local_path)
            else:
                raise ImportError(f"라이브러리 '{lib_name}'을(를) 찾을 수 없습니다. (인증 목록 및 로컬 파일에 없음)")
        
        self.imported_functions[lib_name] = functions
        print(f"✓ 라이브러리 '{lib_name}' 로드 완료.")
        return functions
    
    def import_from_url(self, url: str) -> Dict[str, str]:
        """URL에서 라이브러리를 다운로드하고 파싱합니다."""
        try:
            # URL이 .pyllib으로 끝나지 않으면 추가 (단, 사용자가 의도적으로 다른 확장자를 쓴 경우 주의)
            if not url.endswith('.pyllib'):
                url = url.rstrip('/') + '.pyllib'
            
            # 임시 파일 생성 및 다운로드
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pyllib') as tmp:
                temp_path = tmp.name
                
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as response, open(temp_path, 'wb') as out_file:
                out_file.write(response.read())
            
            functions = self.load_pyllib(temp_path)
            os.unlink(temp_path) # 사용 후 임시 파일 삭제
            return functions
            
        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise ImportError(f"URL '{url}'에서 라이브러리를 가져올 수 없습니다: {e}")
    
    def load_pyllib(self, lib_path: str) -> Dict[str, str]:
        """
        .pyllib 파일(zip 형식)을 로드하여 파이썬 코드를 딕셔너리로 반환합니다.
        """
        if not os.path.exists(lib_path):
            raise FileNotFoundError(f"라이브러리 파일을 찾을 수 없습니다: {lib_path}")
        
        functions = {}
        try:
            with zipfile.ZipFile(lib_path, 'r') as zf:
                for file_info in zf.filelist:
                    # pyfunctions 폴더 안의 .py 파일만 추출
                    if file_info.filename.startswith('pyfunctions/') and file_info.filename.endswith('.py'):
                        func_name = os.path.basename(file_info.filename)[:-3]  # .py 제거
                        code = zf.read(file_info).decode('utf-8')
                        functions[func_name] = code
        except zipfile.BadZipFile:
            raise ImportError(f"유효하지 않은 라이브러리 압축 형식입니다: {lib_path}")
        
        return functions
    
    def execute_function(self, lib_name: str, func_name: str, args: str) -> Any:
        """지정된 라이브러리의 함수를 실행합니다."""
        functions = self.import_library(lib_name)
        
        if func_name not in functions:
            raise AttributeError(f"'{lib_name}' 라이브러리 내에 함수 '{func_name}'이(가) 존재하지 않습니다.")
        
        code = functions[func_name]
        namespace: Dict[str, Any] = {}
        
        try:
            # 외부 코드를 실행합니다.
            exec(code, namespace)
        except Exception as e:
            raise RuntimeError(f"함수 컴파일 오류 ({func_name}): {e}")
        
        # namespace에서 실행 가능한 첫 번째 함수를 찾습니다.
        func = None
        for name, obj in namespace.items():
            if callable(obj) and not name.startswith('_'):
                func = obj
                break
        
        if func is None:
            raise RuntimeError(f"'{func_name}' 내에서 실행 가능한 함수(Callable)를 찾을 수 없습니다.")
        
        try:
            # 전달값을 인자로 넣어 실행합니다. (파이썬 코드 내에서 문자열로 처리된다고 가정)
            result = func(args)
            return result
        except Exception as e:
            raise RuntimeError(f"함수 실행 오류 ({func_name}): {e}")
    
    def parse_and_execute(self, code: str) -> None:
        """Lib.pyl 코드를 파싱하고 한 줄씩 실행합니다."""
        lines = code.strip().split('\n')
        
        for line_num, line in enumerate(lines, start=1):
            # 주석 제거 (^주석 내용^)
            line = re.sub(r'\^.*?\^', '', line).strip()
            
            if not line:
                continue
                
            # 코딩 똑똑이의 수정: end 키워드를 만나면 파싱을 완전히 종료합니다.
            if line == 'end':
                print("▶ 코드 실행 종료 (end 키워드 인식)")
                break
            
            # 패턴 1: import"libname"
            import_match = re.match(r'import\s*"([^"]+)"', line)
            if import_match:
                lib_name = import_match.group(1)
                try:
                    self.import_library(lib_name)
                except Exception as e:
                    print(f"[{line_num}줄] ❌ 임포트 오류: {e}", file=sys.stderr)
                continue
            
            # 패턴 2: "libname"_"funcname"_"args"
            call_match = re.match(r'"([^"]+)"\s*_\s*"([^"]+)"\s*_\s*"([^"]*)"', line)
            if call_match:
                lib_name = call_match.group(1)
                func_name = call_match.group(2)
                args = call_match.group(3)
                
                try:
                    result = self.execute_function(lib_name, func_name, args)
                    if result is not None:
                        print(f"결과: {result}")
                except Exception as e:
                    print(f"[{line_num}줄] ❌ 실행 오류: {e}", file=sys.stderr)
                continue
                
            # 매칭되는 패턴이 없는 구문
            print(f"[{line_num}줄] ⚠ 경고: 알 수 없는 문법입니다 -> '{line}'", file=sys.stderr)

def main():
    # 사용자가 스크립트 실행 시 인자를 넣지 않았을 경우 안내
    if len(sys.argv) < 2:
        print("💡 사용법: python runtime.py <파일명.pyl>")
        sys.exit(1)
    
    pyl_file = sys.argv[1]
    
    if not os.path.exists(pyl_file):
        print(f"❌ 오류: 파일을 찾을 수 없습니다 -> {pyl_file}")
        sys.exit(1)
    
    try:
        with open(pyl_file, 'r', encoding='utf-8') as f:
            code = f.read()
    except Exception as e:
        print(f"❌ 오류: 파일을 읽는 중 문제가 발생했습니다: {e}")
        sys.exit(1)
    
    runtime = LibPylRuntime()
    print("=" * 40)
    print(f"🚀 Lib.pyl 실행 시작: {os.path.basename(pyl_file)}")
    print("=" * 40)
    
    runtime.parse_and_execute(code)

if __name__ == "__main__":
    main()
