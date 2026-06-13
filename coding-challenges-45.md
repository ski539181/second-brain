# Coding Problem Set: 40 Bug Challenges
*Hermes self-improvement, 2026-06-13*

Each problem: subtle bug, real-world, with hint + solution.

---

## 🐍 Python (15)

### 1. Mutable default argument
```python
def add_item(item, cart=[]):
    cart.append(item)
    return cart
print(add_item("apple"))  # ?
print(add_item("banana"))  # ?
```
**Hint:** `cart=[]` evaluated once at def time, not each call.
**Solution:** `def add_item(item, cart=None): if cart is None: cart = []`
**Why tricky:** Looks like normal init pattern, but default mutables persist.

### 2. Late binding closures
```python
funcs = [lambda x: x + i for i in range(3)]
print([f(0) for f in funcs])  # ?
```
**Hint:** Closures capture by reference, not value.
**Solution:** `[lambda x, i=i: x + i for i in range(3)]`
**Why tricky:** All 3 lambdas share same `i`, all return 2.

### 3. Generator exhaustion
```python
gen = (x for x in [1, 2, 3])
list(gen)  # [1, 2, 3]
list(gen)  # ?
```
**Hint:** Generators are single-use iterators.
**Solution:** Re-create: `gen = (x for x in [1, 2, 3])`
**Why tricky:** `list()` consumed it; second call is empty.

### 4. None comparison
```python
def find(items, target):
    for i, x in enumerate(items):
        if x == target: return i
    return -1
print(find([0, None, 2], None))  # ?
```
**Hint:** `x == None` works but `is None` is the idiom.
**Solution:** Use `is None` for None checks.
**Why tricky:** Works, but breaks for `__eq__` overrides; not a bug here but bad practice.

### 5. String interning
```python
a = "hello"
b = "hello"
print(a is b)  # ?
a = "hello world"
b = "hello world"
print(a is b)  # ?
```
**Hint:** CPython interns short strings; long ones usually not.
**Solution:** Use `==` for value comparison, not `is`.
**Why tricky:** Behavior depends on string length and Python version.

### 6. Float equality
```python
total = 0.1 + 0.2
print(total == 0.3)  # ?
```
**Hint:** IEEE 754 floating-point.
**Solution:** `abs(total - 0.3) < 1e-9` or use `decimal.Decimal`.
**Why tricky:** `total` is 0.30000000000000004.

### 7. Dict mutation during iteration
```python
d = {"a": 1, "b": 2, "c": 3}
for k in d:
    if d[k] < 2:
        del d[k]  # RuntimeError!
```
**Hint:** Can't modify dict size during iteration.
**Solution:** `for k in list(d.keys()):` then modify.
**Why tricky:** Sometimes works (Python 3 lazy deletion), but undefined behavior.

### 8. List multiply reference
```python
grid = [[0] * 3] * 3
grid[0][0] = 1
print(grid)  # ?
```
**Hint:** `*` copies references, not values.
**Solution:** `[[0] * 3 for _ in range(3)]`
**Why tricky:** All 3 rows are the SAME list.

### 9. Tuple as dict key (with list)
```python
d = {([1, 2], "a"): 1}  # TypeError!
```
**Hint:** Dict keys must be hashable; lists aren't.
**Solution:** Convert to tuple: `(tuple([1, 2]), "a")`
**Why tricky:** Looks like a tuple already, but contains a list.

### 10. Encoding issues
```python
text = "สวัสดี"
b = text.encode("ascii")  # UnicodeEncodeError!
```
**Hint:** Thai is not ASCII.
**Solution:** `.encode("utf-8")` or `.encode("ascii", errors="ignore")`.
**Why tricky:** Works on English text, fails silently on multilingual data.

### 11. Off-by-one slicing
```python
items = [10, 20, 30, 40, 50]
print(items[1:4])  # ?
print(items[-1:0])  # ?
```
**Hint:** Slicing is [start, stop), stop is exclusive.
**Solution:** `items[-1:0:-1]` to reverse from end to index 1.
**Why tricky:** Negative + zero start confuses intent.

### 12. Sort stability
```python
items = [("a", 2), ("b", 1), ("c", 2)]
print(sorted(items, key=lambda x: x[1]))  # ?
```
**Hint:** Python's sort is stable; ties preserve original order.
**Solution:** Stable, so result is `[("b", 1), ("a", 2), ("c", 2)]`.
**Why tricky:** Some langs sort is unstable; not Python.

### 13. *args mutation
```python
def process(*args):
    args[0] = 99  # TypeError!
```
**Hint:** `*args` is a tuple, immutable.
**Solution:** Use list: `def process(*args): args_list = list(args); args_list[0] = 99`.
**Why tricky:** Looks like a list, but tuple.

### 14. Walrus in comprehension
```python
# This works:
[(y, x/y) for x in range(10) if (y := x + 1) > 0]
# But this doesn't:
result = [(y := x + 1) for x in range(10)]
```
**Hint:** Walrus leaks from comprehension scope (Python 3.8+).
**Solution:** Walrus in comps is fine; just don't depend on leak.
**Why tricky:** Behavior change between Python versions.

### 15. Star in function call
```python
def foo(a, b, c): return a + b + c
data = {"a": 1, "b": 2, "c": 3}
print(foo(**data))  # Works
data2 = {"a": 1, "b": 2, "d": 3}  # typo: 'd' instead of 'c'
print(foo(**data2))  # TypeError
```
**Hint:** `**` requires exact key match.
**Solution:** Use explicit: `foo(data["a"], data["b"], data.get("c", 0))`.
**Why tricky:** Typos in keys fail at call time, not at dict creation.

---

## 🐚 Shell/Bash (8)

### 16. Word splitting
```bash
FILE="my document.txt"
rm $FILE  # WRONG! rm "my" "document.txt"
```
**Hint:** Unquoted vars split on spaces.
**Solution:** `rm "$FILE"`
**Why tricky:** Works fine for files without spaces.

### 17. Subshell variable scope
```bash
count=0
cat file.txt | while read line; do
    count=$((count + 1))
done
echo $count  # 0, not actual count!
```
**Hint:** Pipe runs `while` in subshell; variables don't persist.
**Solution:** `while read line; do ... done < file.txt` (no pipe).
**Why tricky:** Looks like the loop runs in main shell.

### 18. Exit code in pipe
```bash
false | true
echo $?  # 0 (last cmd's exit)
```
**Hint:** Default: `$?` is last command in pipe.
**Solution:** `set -o pipefail` to catch any failure.
**Why tricky:** Errors in middle of pipe silently disappear.

### 19. Quoting arrays
```bash
arr=("a b" "c d")
for x in ${arr[@]}; do echo "$x"; done  # Splits!
```
**Hint:** `${arr[@]}` without quotes splits.
**Solution:** `for x in "${arr[@]}"`.
**Why tricky:** Single-element arrays work fine, multi-element breaks.

### 20. SIGPIPE
```bash
yes | head -5
echo $?  # 141 (SIGPIPE), not 0!
```
**Hint:** `yes` gets killed by SIGPIPE when `head` exits.
**Solution:** Wrap in `|| true` or handle SIGPIPE in script.
**Why tricky:** Error code 141 is non-obvious.

### 21. Race condition in temp files
```bash
TMPFILE="/tmp/myapp-$$"
echo "data" > $TMPFILE
# Another process: same pid reuse → collision!
```
**Hint:** `$$` can be reused; use `mktemp`.
**Solution:** `TMPFILE=$(mktemp)`.
**Why tricky:** Works in tests, fails in production with concurrent runs.

### 22. Set -e edge case
```bash
set -e
[ -f /nonexistent ] && echo "found"
echo "still here?"  # Maybe not!
```
**Hint:** `&&` exempt from `set -e` (treated as conditional).
**Solution:** Don't rely on `set -e` for safety; check explicitly.
**Why tricky:** Looks like set -e protects; it doesn't here.

### 23. For loop glob
```bash
for f in *.txt; do
    echo "$f"
done  # Fails if no .txt files: f = "*.txt"
```
**Hint:** Glob with no matches returns the pattern itself.
**Solution:** `for f in *.txt; do [ -e "$f" ] || continue; ...`.
**Why tricky:** Only triggers when no matches.

---

## ⚡ Async/Concurrency (5)

### 24. Race on shared counter
```python
import asyncio
counter = 0
async def inc():
    global counter
    await asyncio.sleep(0)
    counter += 1
async def main():
    await asyncio.gather(*[inc() for _ in range(100)])
    print(counter)  # < 100, not 100
```
**Hint:** `+=` is read-modify-write, not atomic.
**Solution:** `asyncio.Lock` or use `asyncio.Semaphore`.
**Why tricky:** Single-threaded but still has races (await points).

### 25. Async generator cleanup
```python
async def gen():
    try:
        for i in range(10):
            yield i
    finally:
        print("cleaned up")  # Maybe not called!
async def main():
    async for x in gen():
        if x == 3: break
```
**Hint:** `break` doesn't trigger `__aexit__` properly.
**Solution:** Use `async with agen()` (Python 3.10+).
**Why tricky:** Resource leaks.

### 26. Deadlock with locks
```python
lock_a = threading.Lock()
lock_b = threading.Lock()
def t1():
    with lock_a:
        time.sleep(0.1)
        with lock_b: pass
def t2():
    with lock_b:
        time.sleep(0.1)
        with lock_a: pass
t1(); t2()  # DEADLOCK
```
**Hint:** Lock order matters.
**Solution:** Always acquire in same order (e.g., alphabetical).
**Why tricky:** Works in single-thread tests.

### 27. Thread-safe counter
```python
counter = 0
def inc():
    global counter
    for _ in range(100000):
        counter += 1
threads = [threading.Thread(target=inc) for _ in range(10)]
[t.start() for t in threads]
[t.join() for t in threads]
print(counter)  # < 1,000,000
```
**Hint:** Same as #24 but with threads.
**Solution:** `threading.Lock` or `itertools.count()`.
**Why tricky:** Increment is not atomic.

### 28. asyncio.gather vs TaskGroup
```python
# In gather, one failure doesn't cancel others
async def main():
    try:
        await asyncio.gather(failing(), working())
    except Exception as e:
        pass  # working() may still be running
```
**Hint:** `gather()` doesn't auto-cancel siblings on failure.
**Solution:** `async with asyncio.TaskGroup() as tg: tg.create_task(...)` (3.11+).
**Why tricky:** Resource leaks from unfinished tasks.

---

## 🌐 Web/API (5)

### 29. CORS preflight
```js
fetch('https://api.example.com/data', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({key: 'value'})
})  // CORS error!
```
**Hint:** Custom headers trigger preflight (OPTIONS).
**Solution:** Server must respond to OPTIONS with proper headers.
**Why tricky:** GET works, POST fails mysteriously.

### 30. Rate limit retry
```python
def fetch():
    r = requests.get(url)
    return r.json()  # Fails on 429
```
**Hint:** 429 means try again later.
**Solution:** Retry with backoff: `requests.adapters.HTTPAdapter(max_retries=Retry(...))`.
**Why tricky:** Works in tests, fails in production at scale.

### 31. Streaming response
```python
r = requests.get(url, stream=True)
data = r.json()  # ConnectionError: not fully read
```
**Hint:** `stream=True` requires `r.raw.read()`.
**Solution:** `r.raw.read()` or set `stream=False`.
**Why tricky:** `iter_content` works, `json()` doesn't.

### 32. JSON parse error
```python
r = requests.get(url)
data = r.json()  # Could be HTML error page!
```
**Hint:** Check status before parsing.
**Solution:** `r.raise_for_status(); data = r.json()`.
**Why tricky:** Server returns 200 with error HTML in body.

### 33. Connection pool exhaustion
```python
# Creating session per request
def fetch(url):
    with requests.Session() as s:
        return s.get(url).json()
# For 1000 concurrent calls: connection refused!
```
**Hint:** Reuse session, use connection pooling.
**Solution:** Module-level `SESSION = requests.Session()`.
**Why tricky:** Works for low traffic.

---

## 💾 Database (4)

### 34. SQL injection
```python
cur.execute(f"SELECT * FROM users WHERE name = '{name}'")
# name = "'; DROP TABLE users; --"
```
**Hint:** String interpolation is unsafe.
**Solution:** `cur.execute("SELECT * FROM users WHERE name = ?", (name,))`.
**Why tricky:** Works fine with trusted input.

### 35. N+1 query
```python
for user in users:
    posts = db.query("SELECT * FROM posts WHERE user_id = ?", user.id)
    user.posts = posts  # 1 + N queries!
```
**Hint:** Multiple round-trips.
**Solution:** `SELECT * FROM posts WHERE user_id IN (...)` + group.
**Why tricky:** ORM hides it; performance degrades at scale.

### 36. Transaction isolation
```python
cur.execute("BEGIN")
cur.execute("SELECT balance FROM accounts WHERE id = 1")  # 100
time.sleep(5)
cur.execute("UPDATE accounts SET balance = balance - 50 WHERE id = 1")
cur.execute("COMMIT")
# Meanwhile, another tx added money: lost update!
```
**Hint:** Default isolation (READ COMMITTED) doesn't prevent.
**Solution:** `SELECT ... FOR UPDATE` or higher isolation.
**Why tricky:** Two parallel updates can lose one.

### 37. Connection leak
```python
def get_user(id):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (id,))
    return cur.fetchone()  # conn never closed!
```
**Hint:** No `close()` or context manager.
**Solution:** `with sqlite3.connect(db) as conn: ...` or try/finally.
**Why tricky:** Works in tests; leaks in production.

---

## 📁 File I/O (3)

### 38. File handle leak
```python
for line in open("big.txt"):  # No close!
    process(line)
```
**Hint:** `open()` without close leaks FDs.
**Solution:** `with open("big.txt") as f:` or `f.close()`.
**Why tricky:** Python may close at GC, but not guaranteed; large files hit FD limit.

### 39. Atomic write
```python
with open("config.json", "w") as f:
    json.dump(data, f)
# Crash mid-write → corrupted file!
```
**Hint:** Direct write isn't atomic.
**Solution:** Write to `config.json.tmp`, then `os.replace()`.
**Why tricky:** Crash leaves config unparseable on next start.

### 40. Symlink loop
```python
for root, dirs, files in os.walk("/path"):
    for f in files:
        os.path.getsize(os.path.join(root, f))
# Infinite loop on circular symlinks!
```
**Hint:** `os.walk` follows symlinks by default in Python 3.
**Solution:** `os.walk(path, followlinks=False)`.
**Why tricky:** Walks forever, uses all memory.

---

## 🔒 Bonus: Security (5)

### 41. Path traversal
```python
filename = request.args.get("file")
return send_file(f"/data/{filename}")
# filename = "../../../etc/passwd"
```
**Hint:** User controls path.
**Solution:** `os.path.realpath` check + whitelist.
**Why tricky:** Works for legitimate filenames.

### 42. Command injection
```python
import subprocess
subprocess.run(f"ping {host}", shell=True)
# host = "google.com; rm -rf /"
```
**Hint:** `shell=True` with string interpolation.
**Solution:** `subprocess.run(["ping", host])` (list args, no shell).
**Why tricky:** "Ping by name" is a common feature.

### 43. Pickle deserialization
```python
data = pickle.loads(user_input)
# RCE possible!
```
**Hint:** Pickle can execute arbitrary code.
**Solution:** Use JSON, or HMAC-sign the data.
**Why tricky:** "It's just data, what could go wrong?"

### 44. Timing attack
```python
def check_token(provided):
    if provided == SECRET_TOKEN:  # Compares char-by-char with early exit
        return True
```
**Hint:** `==` is not constant-time.
**Solution:** `hmac.compare_digest(provided, SECRET_TOKEN)`.
**Why tricky:** Timing differences reveal correct prefix.

### 45. Open redirect
```python
return redirect(request.args.get("next"))
# next = "//evil.com"
```
**Hint:** External URL → phishing.
**Solution:** Whitelist allowed redirect targets.
**Why tricky:** Looks fine for internal paths.

---

## 📊 Stats
- 45 problems total (15 Python, 8 Shell, 5 Async, 5 Web, 4 DB, 3 File, 5 Security)
- Difficulty: Medium-Hard
- Real-world relevance: 100%
- Type: 11 categories
- Categories breakdown:
  - 🐍 Python language quirks: 15
  - 🐚 Shell environment: 8
  - ⚡ Concurrency: 5
  - 🌐 HTTP/API: 5
  - 💾 Data: 4
  - 📁 I/O: 3
  - 🔒 Security: 5
