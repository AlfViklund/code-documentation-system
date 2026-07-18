import tempfile
from pathlib import Path
from docify.anchors.symbols import extract_symbols, _hash_body, _normalize, find_symbol

def test_normalize_whitespace():
    code1 = "def  hello( a,   b ):\n    return   a + b\n"
    code2 = "def hello(a,b):\n    return a+b\n"
    # Normalization strips extra spaces around operators & whitespace
    assert _normalize(code1) == _normalize(code2)

def test_normalize_string_literal_whitespace_limitation():
    # Known edge case: regex normalization operates on full symbol text without string literal awareness
    code1 = 'def msg(): return "hello  world"'
    code2 = 'def msg(): return "hello world"'
    assert _normalize(code1) == _normalize(code2)

def test_extract_python_symbols():
    code = '''
def top_function(x):
    return x * 2

class SampleService:
    def process_data(self, item):
        print("processing")
        return True
'''
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tmp:
        tmp.write(code)
        tmp.flush()
        tmp_path = Path(tmp.name)

    symbols = extract_symbols(tmp_path, "sample.py")
    symbol_names = [s.qualified_name for s in symbols]
    assert "top_function" in symbol_names
    assert "SampleService.process_data" in symbol_names
    tmp_path.unlink()

def test_symbol_hash_invariant_on_rename():
    # Changing function name from foo to bar should yield the SAME body hash
    # because the symbol name node is stripped during _hash_body.
    code_foo = '''
def foo(a, b):
    print("hello world")
    return a + b
'''
    code_bar = '''
def bar(a, b):
    print("hello world")
    return a + b
'''
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tmp1, \
         tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tmp2:
        tmp1.write(code_foo)
        tmp1.flush()
        tmp2.write(code_bar)
        tmp2.flush()
        
        sym1 = find_symbol(Path(tmp1.name), "test1.py", "foo")
        sym2 = find_symbol(Path(tmp2.name), "test2.py", "bar")

    assert sym1 is not None
    assert sym2 is not None
    assert sym1.body_hash == sym2.body_hash
    Path(tmp1.name).unlink()
    Path(tmp2.name).unlink()
