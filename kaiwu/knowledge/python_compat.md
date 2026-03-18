# Python Library Version Compatibility Guide

Common breaking changes, migration paths, and pitfalls across popular Python libraries.

---

## marshmallow 3.x (Breaking Changes)

```python
# OLD (2.x) - will raise deprecation warnings or errors
name = fields.Str(missing="default")
age  = fields.Int(missing=0)

# NEW (3.x) - correct usage
name = fields.Str(load_default="default")
age  = fields.Int(load_default=0)
```
- `required=True` is set directly on the field, not via `validate`
- `@post_load` returns a dict by default, not an object (unless you manually construct one)
- `@post_load` method signature must include `**kwargs`: `def make_obj(self, data, **kwargs)`
- Install: `pip install marshmallow` (not `flask-marshmallow`, unless you need Flask integration)

---

## SQLAlchemy 2.x (Breaking Changes)

```python
# OLD (1.x) - deprecated
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

# NEW - Flask-SQLAlchemy pattern (recommended for Flask apps)
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()
class Todo(db.Model):
    __tablename__ = 'todos'
    id = db.Column(db.Integer, primary_key=True)

# NEW - Pure SQLAlchemy 2.x pattern
from sqlalchemy.orm import DeclarativeBase
class Base(DeclarativeBase): pass
```
- Flask-SQLAlchemy: call `db.init_app(app)` after app creation
- Save records: `db.session.add()` + `db.session.commit()`
- Query: `Todo.query.all()` or `db.session.execute(select(Todo)).scalars().all()`

---

## pycrypto -> pycryptodome Migration

```bash
# pycrypto is abandoned and will fail to install
pip install pycrypto  # DO NOT USE

# pycryptodome is the drop-in replacement (same import paths)
pip install pycryptodome
```
```python
from Crypto.Cipher import AES   # import path unchanged
from Crypto.Random import get_random_bytes
```

---

## concurrent.futures Standard Patterns

```python
import concurrent.futures

def process(item):
    return item  # actual processing logic

# Standard pattern - ThreadPoolExecutor
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    results = list(executor.map(process, items))

# Pattern with error handling
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(process, item): item for item in items}
    results = []
    for future in concurrent.futures.as_completed(futures):
        try:
            results.append(future.result())
        except Exception as e:
            print(f"Error: {e}")
```
- Prefer `ThreadPoolExecutor` over raw `threading.Thread` for concurrent tasks
- Always set `max_workers` explicitly; do not rely on the default value
- Use `ProcessPoolExecutor` for CPU-bound work (but beware of pickling constraints)

---

## Flask Common Pitfalls

```python
# app.py standard structure
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todos.db'
db = SQLAlchemy()
db.init_app(app)
CORS(app)

with app.app_context():
    db.create_all()  # MUST be inside app context

@app.route('/todos', methods=['GET'])
def get_todos():
    todos = Todo.query.all()
    return jsonify([{'id': t.id, 'title': t.title} for t in todos])

@app.route('/todos', methods=['POST'])
def create_todo():
    data = request.get_json()
    todo = Todo(title=data['title'])
    db.session.add(todo)
    db.session.commit()
    return jsonify({'id': todo.id}), 201
```

**Key pitfalls:**
- `db.create_all()` and other DB operations require an active app context
- `CORS(app)` must be called to allow cross-origin requests from frontends
- `request.get_json()` returns `None` if Content-Type is not `application/json`
- Circular imports: avoid importing `app` in model files; use `db.init_app(app)` pattern

---

## pytest Common Pitfalls

```python
# conftest.py - shared fixtures
import pytest

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as c:
        with app.app_context():
            db.create_all()
        yield c

# test file
def test_get_todos(client):
    response = client.get('/todos')
    assert response.status_code == 200
```

**Key pitfalls:**
- Fixtures in `conftest.py` are auto-discovered; do not import them manually
- Use `yield` in fixtures for setup/teardown; code after `yield` runs as cleanup
- `scope="session"` or `scope="module"` fixtures persist across tests -- careful with mutable state
- Test files must be named `test_*.py` or `*_test.py` to be discovered
- Test functions must start with `test_`

---

## Common Import Traps

- **datetime**: `datetime.datetime.now()` is not the same as `datetime.now()` -- you need `from datetime import datetime` or use the full module path
- **json**: `json.dumps()` escapes non-ASCII by default; add `ensure_ascii=False` for readable Chinese/Unicode output
- **pathlib**: `pathlib.Path` supports `/` operator on Windows, but `os.path.join` is more universally compatible in older codebases
- **open()**: On Windows, default encoding is GBK (CP936); always specify `encoding='utf-8'` explicitly
- **collections**: `from collections import Mapping` removed in Python 3.10+; use `from collections.abc import Mapping`
- **typing**: `typing.Optional[X]` is equivalent to `Union[X, None]`, not "the argument is optional"

---

## Dependency Verification Template

```bash
# Verify dependencies are installed and check versions
python -c "import Crypto; print('pycryptodome OK')"
python -c "import flask; print('flask', flask.__version__)"
python -c "import marshmallow; print('marshmallow', marshmallow.__version__)"
python -c "import sqlalchemy; print('sqlalchemy', sqlalchemy.__version__)"

# Install missing dependencies
pip install pycryptodome flask flask-sqlalchemy marshmallow flask-cors
```

**Version pinning best practice:**
```
# requirements.txt - pin major.minor, allow patch updates
flask>=3.0,<4.0
sqlalchemy>=2.0,<3.0
marshmallow>=3.0,<4.0
```
