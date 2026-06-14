# Fine-Tune Dataset Vol.2: 20 Advanced System-Level Coding Problems
> Role: Senior System-Level Coding Expert | Node.js ESM | Difficulty: Expert
> ไม่ซ้ำกับ Vol.1

---
## ENTRY 001 — Raft Consensus Algorithm

### PROMPT
```
Implement Raft consensus: Leader Election, Log Replication, Safety, Recovery
```

### [Thinking & Logic]

**3 Sub-problems:**
```
1. Leader Election
   Follower → (timeout) → Candidate → (majority vote) → Leader
   term = logical clock, เพิ่มทุก election

2. Log Replication
   Leader ← client write → append log → AppendEntries RPC → majority ACK → commit

3. Safety
   Election Restriction: Candidate ต้องมี log up-to-date กว่า majority
   Leader Completeness: committed entry ต้องอยู่ใน all future leaders
```

**State Machine:**
```
CLOSED(normal) → (10 failures) → OPEN(reject all) → (60s) → HALF_OPEN → (test) → CLOSED
```

**Log Entry:** `{ index, term, command }`
**AppendEntries:** prevLogIndex/Term ต้องตรงก่อน append (Log Matching Property)

### [Implementation]

```javascript
// raft.js
import { EventEmitter } from "events";

const State = { FOLLOWER:"F", CANDIDATE:"C", LEADER:"L" };
const rand  = (min,max) => min + Math.random()*(max-min);

class RaftNode extends EventEmitter {
  constructor(id, peers, net) {
    super();
    this.id          = id;
    this.peers       = peers;          // Set<id>
    this.net         = net;            // { send(to,msg), on(fn) }
    // Persistent
    this.currentTerm = 0;
    this.votedFor    = null;
    this.log         = [{ index:0, term:0, cmd:null }]; // sentinel
    // Volatile
    this.state       = State.FOLLOWER;
    this.commitIndex = 0;
    this.lastApplied = 0;
    this.leader      = null;
    // Leader only
    this.nextIndex   = new Map();
    this.matchIndex  = new Map();
    // Election
    this.votes       = new Set();
    this.sm          = {};             // state machine (key-value)

    net.on((msg) => this._recv(msg));
    this._resetTimer();
  }

  // ── Timer ──────────────────────────────────────────────────
  _resetTimer() {
    clearTimeout(this._et);
    this._et = setTimeout(() => this._elect(), rand(150,300));
  }

  // ── Election ───────────────────────────────────────────────
  _elect() {
    this.currentTerm++;
    this.state    = State.CANDIDATE;
    this.votedFor = this.id;
    this.votes    = new Set([this.id]);
    this.leader   = null;
    const last    = this.log.at(-1);
    for (const p of this.peers) {
      this.net.send(p, {
        type:"RV", term:this.currentTerm, from:this.id,
        lastIndex:last.index, lastTerm:last.term
      });
    }
    this._resetTimer();
  }

  // ── Become Leader ─────────────────────────────────────────
  _becomeLeader() {
    clearTimeout(this._et);
    this.state  = State.LEADER;
    this.leader = this.id;
    for (const p of this.peers) {
      this.nextIndex.set(p, this.log.length);
      this.matchIndex.set(p, 0);
    }
    this.emit("leader", { term:this.currentTerm, id:this.id });
    // Append no-op to commit previous entries
    this.log.push({ index:this.log.length, term:this.currentTerm, cmd:null });
    this._heartbeat();
  }

  // ── Heartbeat ─────────────────────────────────────────────
  _heartbeat() {
    if (this.state !== State.LEADER) return;
    for (const p of this.peers) this._sendAE(p);
    this._ht = setTimeout(() => this._heartbeat(), 50);
  }

  _sendAE(peer) {
    const ni   = this.nextIndex.get(peer) ?? 1;
    const prev = this.log[ni-1] ?? this.log[0];
    this.net.send(peer, {
      type:"AE", term:this.currentTerm, from:this.id,
      prevIndex:prev.index, prevTerm:prev.term,
      entries:this.log.slice(ni), commit:this.commitIndex
    });
  }

  // ── Client Submit ─────────────────────────────────────────
  submit(cmd) {
    if (this.state !== State.LEADER)
      return Promise.reject(new Error(`Not leader, try ${this.leader}`));
    const entry = { index:this.log.length, term:this.currentTerm, cmd };
    this.log.push(entry);
    return new Promise((res,rej) => {
      const check = () => {
        if (this.commitIndex >= entry.index) { this.off("applied",check); res(entry); }
      };
      this.on("applied", check);
      setTimeout(() => { this.off("applied",check); rej(new Error("Timeout")); }, 5000);
    });
  }

  // ── Message Handler ───────────────────────────────────────
  _recv(msg) {
    if (msg.term > this.currentTerm) {
      this.currentTerm = msg.term;
      this._toFollower();
    }
    switch (msg.type) {
      case "RV":  this._onRequestVote(msg);         break;
      case "RVR": this._onRequestVoteReply(msg);    break;
      case "AE":  this._onAppendEntries(msg);       break;
      case "AER": this._onAppendEntriesReply(msg);  break;
    }
  }

  _onRequestVote(msg) {
    const myLast = this.log.at(-1);
    const upToDate =
      msg.lastTerm > myLast.term ||
      (msg.lastTerm === myLast.term && msg.lastIndex >= myLast.index);
    const grant =
      msg.term >= this.currentTerm &&
      (!this.votedFor || this.votedFor === msg.from) &&
      upToDate;
    if (grant) { this.votedFor = msg.from; this._resetTimer(); }
    this.net.send(msg.from, { type:"RVR", term:this.currentTerm, grant, from:this.id });
  }

  _onRequestVoteReply(msg) {
    if (this.state !== State.CANDIDATE || msg.term !== this.currentTerm) return;
    if (msg.grant) {
      this.votes.add(msg.from);
      if (this.votes.size >= Math.floor((this.peers.size+1)/2)+1)
        this._becomeLeader();
    }
  }

  _onAppendEntries(msg) {
    this._resetTimer();
    this.leader = msg.from;
    if (msg.term < this.currentTerm) {
      this.net.send(msg.from,{type:"AER",term:this.currentTerm,ok:false,from:this.id}); return;
    }
    this._toFollower();
    const prev = this.log[msg.prevIndex];
    if (!prev || prev.term !== msg.prevTerm) {
      this.net.send(msg.from,{type:"AER",term:this.currentTerm,ok:false,from:this.id,conflict:msg.prevIndex}); return;
    }
    for (const e of msg.entries) {
      if (this.log[e.index]?.term !== e.term) this.log.length = e.index;
      if (!this.log[e.index]) this.log.push(e);
    }
    if (msg.commit > this.commitIndex) {
      this.commitIndex = Math.min(msg.commit, this.log.length-1);
      this._apply();
    }
    this.net.send(msg.from,{type:"AER",term:this.currentTerm,ok:true,from:this.id,match:this.log.length-1});
  }

  _onAppendEntriesReply(msg) {
    if (this.state !== State.LEADER) return;
    if (msg.ok) {
      this.matchIndex.set(msg.from, msg.match);
      this.nextIndex.set(msg.from, msg.match+1);
      this._maybeCommit();
    } else {
      this.nextIndex.set(msg.from, Math.max(1,(this.nextIndex.get(msg.from)||1)-1));
      this._sendAE(msg.from);
    }
  }

  _maybeCommit() {
    for (let n=this.log.length-1; n>this.commitIndex; n--) {
      if (this.log[n]?.term !== this.currentTerm) continue;
      let cnt=1;
      for (const m of this.matchIndex.values()) if(m>=n) cnt++;
      if (cnt >= Math.floor((this.peers.size+1)/2)+1) {
        this.commitIndex=n; this._apply(); break;
      }
    }
  }

  _apply() {
    while (this.lastApplied < this.commitIndex) {
      this.lastApplied++;
      const e = this.log[this.lastApplied];
      if (e?.cmd?.op==="SET") this.sm[e.cmd.key]=e.cmd.val;
      if (e?.cmd?.op==="DEL") delete this.sm[e.cmd.key];
      this.emit("applied", e);
    }
  }

  _toFollower() {
    clearTimeout(this._ht);
    this.state    = State.FOLLOWER;
    this.votedFor = null;
  }

  status() {
    return { id:this.id, state:this.state, term:this.currentTerm,
             leader:this.leader, logLen:this.log.length, commit:this.commitIndex };
  }

  stop() { clearTimeout(this._et); clearTimeout(this._ht); }
}

// ── In-process Transport ──────────────────────────────────────
class InProcNet {
  constructor() { this.nodes = new Map(); }
  register(id,node) { this.nodes.set(id,node); }
  forNode(id) {
    const self=this; let handler;
    return {
      send(to,msg) { setTimeout(()=>self.nodes.get(to)?._recv(msg), Math.random()*8); },
      on(fn)       { handler=fn; },
      _recv(msg)   { handler?.(msg); }
    };
  }
}

// ── Demo ──────────────────────────────────────────────────────
const net   = new InProcNet();
const ids   = ["A","B","C","D","E"];
const nodes = new Map();

for (const id of ids) {
  const n = new InProcNet().forNode?.(id) || net.forNode(id); // reuse net
  nodes.set(id, new RaftNode(id, new Set(ids.filter(x=>x!==id)), net.forNode(id)));
}
// Re-register with real net
for (const [id,node] of nodes) net.register(id,node);

let leaderNode;
await new Promise(res => {
  for (const n of nodes.values()) n.on("leader", async ({id,term}) => {
    console.log(`✅ Leader: ${id} term=${term}`);
    leaderNode = nodes.get(id);
    res();
  });
});

await leaderNode.submit({op:"SET",key:"x",val:42});
await leaderNode.submit({op:"SET",key:"y",val:"hello"});
nodes.forEach((n,id)=>console.log(`${id} sm:`,n.sm));
for (const n of nodes.values()) n.stop();
```

---

---
## ENTRY 002 — LSM Tree (Log-Structured Merge-Tree)

### PROMPT
```
สร้าง LSM Tree: MemTable (SkipList) + WAL + SSTable + Compaction + Bloom Filter
```

### [Thinking & Logic]

**Write Path:** Write → WAL (durability) → MemTable (sorted) → full? → SSTable (L0)
**Read Path:** MemTable → Bloom Filter per SSTable → SSTable binary search
**Compaction (Leveled):**
```
L0: max 4 SSTables (key range overlap OK)
L1: max 10MB, no overlap within level
Merge sort → new SSTable → delete old files
```
**Bloom Filter:** ก่อน seek SSTable ตรวจ "key possibly exists?" → skip ถ้า "definitely not"

### [Implementation]

```javascript
// lsm.js
import fs from "fs/promises";
import path from "path";

// ── Skip List ─────────────────────────────────────────────────
const MAX_LVL = 16;
class SLNode { constructor(k,v,l) { this.k=k; this.v=v; this.fwd=new Array(l).fill(null); } }
class SkipList {
  constructor() { this.head=new SLNode(-Infinity,null,MAX_LVL); this.lvl=1; this.size=0; }
  _lvl() { let l=1; while(Math.random()<0.5&&l<MAX_LVL)l++; return l; }
  set(k,v) {
    const upd=new Array(MAX_LVL).fill(null);
    let c=this.head;
    for(let i=this.lvl-1;i>=0;i--){ while(c.fwd[i]?.k<k) c=c.fwd[i]; upd[i]=c; }
    c=c.fwd[0];
    if(c?.k===k){ c.v=v; return; }
    const nl=this._lvl();
    if(nl>this.lvl){ for(let i=this.lvl;i<nl;i++) upd[i]=this.head; this.lvl=nl; }
    const n=new SLNode(k,v,nl);
    for(let i=0;i<nl;i++){ n.fwd[i]=upd[i].fwd[i]; upd[i].fwd[i]=n; }
    this.size++;
  }
  get(k) {
    let c=this.head;
    for(let i=this.lvl-1;i>=0;i--) while(c.fwd[i]?.k<k) c=c.fwd[i];
    return c.fwd[0]?.k===k ? c.fwd[0].v : undefined;
  }
  *[Symbol.iterator]() { let c=this.head.fwd[0]; while(c){ yield [c.k,c.v]; c=c.fwd[0]; } }
}

// ── Simple Bloom Filter ───────────────────────────────────────
class Bloom {
  constructor(n=1000) {
    this.m=n*10; this.bits=new Uint8Array(Math.ceil(this.m/8));
  }
  _h(s,seed) {
    let h=seed;
    for(const c of String(s)) h=Math.imul(h^c.charCodeAt(0),0x9e3779b9)>>>0;
    return h%this.m;
  }
  add(k) { [0,1,2].forEach(s=>{ const p=this._h(k,s); this.bits[p>>3]|=1<<(p&7); }); }
  has(k) { return [0,1,2].every(s=>{ const p=this._h(k,s); return (this.bits[p>>3]>>(p&7))&1; }); }
}

// ── SSTable ───────────────────────────────────────────────────
class SSTable {
  constructor(file,bloom,minK,maxK,seq) {
    this.file=file; this.bloom=bloom;
    this.minK=minK; this.maxK=maxK; this.seq=seq; this.level=0;
  }
  mightHave(k) { return k>=this.minK && k<=this.maxK && this.bloom.has(String(k)); }
  async get(k) {
    if(!this.mightHave(k)) return undefined;
    const txt=await fs.readFile(this.file,"utf-8").catch(()=>"");
    for(const line of txt.split("\n").filter(Boolean)){
      const e=JSON.parse(line);
      if(e.k===k) return e.del?undefined:e.v;
      if(e.k>k) break;
    }
    return undefined;
  }
  async *scan() {
    const txt=await fs.readFile(this.file,"utf-8").catch(()=>"");
    for(const line of txt.split("\n").filter(Boolean)) yield JSON.parse(line);
  }
}

// ── LSM Engine ────────────────────────────────────────────────
export class LSM {
  constructor(dir, opts={}) {
    this.dir       = dir;
    this.limit     = opts.memLimit || 500;
    this.l0Limit   = opts.l0Limit || 4;
    this.mem       = new SkipList();
    this.imm       = null;
    this.levels    = [[],[],[]];  // L0, L1, L2
    this.seq       = 0;
    this.wal       = null;
  }

  async init() {
    await fs.mkdir(this.dir,{recursive:true});
    this.wal = await fs.open(path.join(this.dir,"wal.log"),"a");
    await this._recover();
  }

  async put(k,v) {
    await this.wal.write(JSON.stringify({op:"P",k,v,s:++this.seq})+"\n");
    this.mem.set(k,{v,s:this.seq,del:false});
    if(this.mem.size>=this.limit) await this._flush();
  }

  async del(k) {
    await this.wal.write(JSON.stringify({op:"D",k,s:++this.seq})+"\n");
    this.mem.set(k,{v:null,s:this.seq,del:true});
    if(this.mem.size>=this.limit) await this._flush();
  }

  async get(k) {
    // 1. MemTable
    let m=this.mem.get(k);
    if(m!==undefined) return m.del?undefined:m.v;
    // 2. Immutable MemTable
    if(this.imm){ m=this.imm.get(k); if(m!==undefined) return m.del?undefined:m.v; }
    // 3. SSTables newest first
    for(const lvl of this.levels){
      for(const sst of [...lvl].sort((a,b)=>b.seq-a.seq)){
        const val=await sst.get(k);
        if(val!==undefined) return val;
      }
    }
    return undefined;
  }

  // ── Flush MemTable → L0 SSTable ───────────────────────────
  async _flush() {
    this.imm = this.mem; this.mem = new SkipList();
    const entries=[...this.imm];
    const bloom=new Bloom(entries.length);
    const file=path.join(this.dir,`sst-${++this.seq}.log`);
    const lines=entries.map(([k,e])=>{
      bloom.add(String(k));
      return JSON.stringify({k,v:e.v,del:e.del,s:e.s});
    });
    await fs.writeFile(file,lines.join("\n")+"\n");
    const keys=entries.map(([k])=>k);
    this.levels[0].push(new SSTable(file,bloom,keys[0],keys.at(-1),this.seq));
    this.imm=null;
    // Truncate WAL
    await this.wal.close();
    await fs.writeFile(path.join(this.dir,"wal.log"),"");
    this.wal=await fs.open(path.join(this.dir,"wal.log"),"a");
    if(this.levels[0].length>=this.l0Limit) await this._compact(0);
  }

  // ── Compaction: merge L[n] → L[n+1] ─────────────────────
  async _compact(lvl) {
    const src=[...this.levels[lvl]]; this.levels[lvl]=[];
    const merged=new Map();
    for(const sst of src){
      for await(const e of sst.scan()){
        const ex=merged.get(e.k);
        if(!ex||e.s>ex.s) merged.set(e.k,e);
      }
    }
    const sorted=[...merged.values()].sort((a,b)=>a.k<b.k?-1:1).filter(e=>!e.del);
    if(sorted.length>0){
      const bloom=new Bloom(sorted.length);
      const file=path.join(this.dir,`sst-${++this.seq}-l${lvl+1}.log`);
      await fs.writeFile(file, sorted.map(e=>{ bloom.add(String(e.k)); return JSON.stringify(e); }).join("\n")+"\n");
      const sst=new SSTable(file,bloom,sorted[0].k,sorted.at(-1).k,this.seq);
      sst.level=lvl+1;
      this.levels[lvl+1].push(sst);
    }
    for(const s of src) await fs.unlink(s.file).catch(()=>{});
  }

  async _recover() {
    try{
      const txt=await fs.readFile(path.join(this.dir,"wal.log"),"utf-8");
      for(const line of txt.split("\n").filter(Boolean)){
        const e=JSON.parse(line);
        this.seq=Math.max(this.seq,e.s);
        this.mem.set(e.k, e.op==="P"?{v:e.v,s:e.s,del:false}:{v:null,s:e.s,del:true});
      }
    } catch{}
  }
}

// Usage
const db=new LSM("./lsm-db",{memLimit:100});
await db.init();
for(let i=0;i<200;i++) await db.put(`k${i.toString().padStart(3,"0")}`,{n:i});
console.log("k042:", await db.get("k042"));
await db.del("k042");
console.log("After del:", await db.get("k042")); // undefined
```

---
## ENTRY 003 — Lock-Free MPSC Queue (SharedArrayBuffer + Atomics)

### PROMPT
```
สร้าง Lock-Free Data Structures: SPSC Queue, MPSC Queue, Treiber Stack
พร้อม ABA problem detection, memory ordering semantics
```

### [Thinking & Logic]

**CAS Loop Pattern:**
```
do {
  old = Atomics.load(ptr)
  new = compute(old)
} while (Atomics.compareExchange(ptr, old, new) !== old)
→ retry ถ้ามี concurrent modification
```

**ABA Problem:**
```
T1 reads head=A, pause
T2: pop A, push B, pop B, push A (same address!)
T1: CAS(head, A, next_A) succeeds → wrong!
Fix: tag pointer = (ptr << 16 | version), version++ on every CAS
```

**SPSC Queue:** Producer writes tail, Consumer reads head
→ Only ONE writer of tail, ONE reader of head → no CAS needed, just memory barriers

### [Implementation]

```javascript
// lockfree.js

// ── SPSC Ring Buffer (zero-CAS, cache-line friendly) ──────────
export class SPSCQueue {
  constructor(cap, itemBytes=4) {
    if((cap&(cap-1))!==0) throw new Error("capacity must be power of 2");
    this.cap=cap; this.mask=cap-1; this.iSize=itemBytes;
    // Layout: [head(4 bytes)] [64-byte padding] [tail(4)] [64-byte pad] [data]
    this.buf  = new SharedArrayBuffer(128+cap*itemBytes);
    this.ctrl = new Int32Array(this.buf,0,2);   // [head@0, tail@4] NOT USED - use separate
    // Better: separate cache lines for head and tail
    this.hBuf = new SharedArrayBuffer(64);      // head lives alone in its cache line
    this.tBuf = new SharedArrayBuffer(64);      // tail lives alone in its cache line
    this.head = new Int32Array(this.hBuf);
    this.tail = new Int32Array(this.tBuf);
    this.data = new Uint8Array(this.buf, 128);
  }

  enqueue(bytes) {   // Producer only
    const t    = Atomics.load(this.tail, 0);
    const next = (t+1) & this.mask;
    if(next === Atomics.load(this.head, 0)) return false; // full
    const off = t*this.iSize;
    bytes.forEach((b,i)=>{ this.data[off+i]=b; });
    Atomics.store(this.tail, 0, next);           // release store
    return true;
  }

  dequeue(out) {     // Consumer only
    const h = Atomics.load(this.head, 0);
    if(h === Atomics.load(this.tail, 0)) return false; // empty (acquire load)
    const off = h*this.iSize;
    for(let i=0;i<this.iSize;i++) out[i]=this.data[off+i];
    Atomics.store(this.head, 0, (h+1)&this.mask); // release store
    return true;
  }

  get size() {
    const h=Atomics.load(this.head,0), t=Atomics.load(this.tail,0);
    return (t-h+this.cap)&this.mask;
  }
}

// ── MPSC Queue (Multiple Producers, Single Consumer) ──────────
export class MPSCQueue {
  constructor(cap) {
    this.cap  = cap;
    // Each slot: [seq(4), value(4)] → 8 bytes
    this.buf  = new SharedArrayBuffer(8 + cap*8);
    this.meta = new Int32Array(this.buf, 0, 2);   // [enqPos, deqPos]
    this.data = new Int32Array(this.buf, 8);       // [seq0,val0, seq1,val1, ...]
    // Init sequence numbers: slot i expects seq i initially
    for(let i=0;i<cap;i++) Atomics.store(this.data, i*2, i);
  }

  enqueue(value) {
    let pos;
    // CAS to claim slot
    while(true) {
      pos = Atomics.load(this.meta, 0);
      const seq = Atomics.load(this.data, (pos%this.cap)*2);
      const diff = seq - pos;
      if(diff===0){
        // Slot is ready: CAS to claim
        if(Atomics.compareExchange(this.meta,0,pos,pos+1)===pos) break;
      } else if(diff<0) {
        return false; // full
      }
      // diff>0: another producer claimed this slot, retry
    }
    const slot=(pos%this.cap)*2;
    Atomics.store(this.data, slot+1, value);          // write value
    Atomics.store(this.data, slot,   pos+1);          // publish (seq = pos+1)
    return true;
  }

  dequeue() {  // single consumer only
    const pos = Atomics.load(this.meta, 1);
    const slot = (pos%this.cap)*2;
    // Wait for producer to publish
    let spins=0;
    while(Atomics.load(this.data,slot) !== pos+1) {
      if(++spins>1000) return null; // not ready yet
    }
    const val = Atomics.load(this.data, slot+1);
    Atomics.store(this.data, slot, pos+this.cap);     // mark slot as reusable
    Atomics.store(this.meta, 1, pos+1);
    return val;
  }
}

// ── Lock-Free Stack (Treiber's Algorithm) ─────────────────────
export class LFStack {
  constructor(cap=1000) {
    // [top(4)] + [val0, val1, ...] (4 bytes each)
    this.buf  = new SharedArrayBuffer(4*(1+cap));
    this.meta = new Int32Array(this.buf, 0, 1);   // top index
    this.data = new Int32Array(this.buf, 4);
    this.cap  = cap;
  }

  push(val) {
    let top;
    do {
      top = Atomics.load(this.meta, 0);
      if(top>=this.cap) return false;
      Atomics.store(this.data, top, val);
    } while(Atomics.compareExchange(this.meta,0,top,top+1)!==top);
    return true;
  }

  pop() {
    let top;
    do {
      top = Atomics.load(this.meta, 0);
      if(top===0) return null;
    } while(Atomics.compareExchange(this.meta,0,top,top-1)!==top);
    return Atomics.load(this.data, top-1);
  }

  get size() { return Atomics.load(this.meta,0); }
}

// ── Benchmark ─────────────────────────────────────────────────
const q = new SPSCQueue(1024, 4);
const buf=new Uint8Array([1,2,3,4]), out=new Uint8Array(4);
let enq=0,deq=0;
const t0=Date.now();
for(let i=0;i<500000;i++){
  if(q.enqueue(buf)) enq++;
  if(q.dequeue(out)) deq++;
}
const ms=Date.now()-t0;
console.log(`SPSC: ${enq} enq, ${deq} deq in ${ms}ms = ${((enq+deq)/ms*1000)|0} ops/s`);

const stack=new LFStack(10000);
for(let i=0;i<1000;i++) stack.push(i);
console.log(`Stack size=${stack.size}, top=${stack.pop()}`);

const mpsc=new MPSCQueue(256);
for(let i=0;i<100;i++) mpsc.enqueue(i*2);
console.log(`MPSC deq: ${mpsc.dequeue()}, ${mpsc.dequeue()}`);
```

---
## ENTRY 004 — Neural Network Autograd Engine

### PROMPT
```
สร้าง Neural Network from scratch: Tensor + Autograd + Linear + ReLU + Adam
Train XOR problem ให้ accuracy 100%
```

### [Thinking & Logic]

**Computational Graph:**
```
forward:  y = W·x + b → ReLU → loss
backward: ∂loss/∂W = chain rule (backprop through recorded ops)
```

**Chain Rule:**
```
L = f(g(x))
∂L/∂x = ∂L/∂f · ∂f/∂g · ∂g/∂x
→ store _backward() fn ที่แต่ละ op → call in reverse topo order
```

**Adam:** m = β1·m + (1-β1)·g ; v = β2·v + (1-β2)·g²
θ -= lr · m̂/( √v̂ + ε) → bias-corrected first/second moments

### [Implementation]

```javascript
// nn.js

// ── Tensor with autograd ──────────────────────────────────────
class T {
  constructor(data, rg=false) {
    this.d  = Array.isArray(data[0]) ? data : [data];
    this.s  = [this.d.length, this.d[0].length];
    this.g  = null;
    this.rg = rg;
    this._b = ()=>{};
    this._p = [];
  }
  static zeros(r,c) { return new T(Array.from({length:r},()=>new Array(c).fill(0))); }
  static randn(r,c,s=0.1) {
    return new T(Array.from({length:r},()=>Array.from({length:c},()=>(Math.random()*2-1)*s)),true);
  }

  _ensureGrad() { if(!this.g) this.g=T.zeros(...this.s).d; }

  matmul(B) {
    const [m,n]=this.s, [,p]=B.s;
    const out=Array.from({length:m},()=>new Array(p).fill(0));
    for(let i=0;i<m;i++) for(let k=0;k<n;k++) for(let j=0;j<p;j++)
      out[i][j]+=this.d[i][k]*B.d[k][j];
    const R=new T(out); R._p=[this,B];
    R._b=()=>{
      if(this.rg){ this._ensureGrad(); for(let i=0;i<m;i++) for(let k=0;k<n;k++) for(let j=0;j<p;j++) this.g[i][k]+=R.g[i][j]*B.d[k][j]; }
      if(B.rg){    B._ensureGrad();    for(let k=0;k<n;k++) for(let j=0;j<p;j++) for(let i=0;i<m;i++) B.g[k][j]+=this.d[i][k]*R.g[i][j]; }
    };
    return R;
  }

  add(B) {
    const out=this.d.map((r,i)=>r.map((v,j)=>v+(B.d[i]?.[j]??B.d[0][j])));
    const R=new T(out); R._p=[this,B];
    R._b=()=>{
      if(this.rg){ this._ensureGrad(); R.g.forEach((r,i)=>r.forEach((g,j)=>this.g[i][j]+=g)); }
      if(B.rg){    B._ensureGrad();    R.g.forEach(r=>r.forEach((g,j)=>B.g[0][j]+=g)); }
    };
    return R;
  }

  relu() {
    const out=this.d.map(r=>r.map(v=>Math.max(0,v)));
    const R=new T(out); R._p=[this];
    R._b=()=>{ if(this.rg){ this._ensureGrad(); this.d.forEach((r,i)=>r.forEach((v,j)=>this.g[i][j]+=v>0?R.g[i][j]:0)); } };
    return R;
  }

  sigmoid() {
    const sig=v=>1/(1+Math.exp(-v));
    const out=this.d.map(r=>r.map(sig));
    const R=new T(out); R._p=[this];
    R._b=()=>{ if(this.rg){ this._ensureGrad(); R.d.forEach((r,i)=>r.forEach((s,j)=>this.g[i][j]+=s*(1-s)*R.g[i][j])); } };
    return R;
  }

  mseLoss(Y) {
    const [m,n]=this.s;
    const diff=this.d.map((r,i)=>r.map((v,j)=>v-Y.d[i][j]));
    const loss=diff.flat().reduce((s,v)=>s+v*v,0)/(m*n);
    const R=new T([[loss]]); R._p=[this];
    R._b=()=>{ if(this.rg){ this._ensureGrad(); diff.forEach((r,i)=>r.forEach((d,j)=>this.g[i][j]+=2*d/(m*n))); } };
    return R;
  }

  backward() {
    if(!this.g) this.g=[[1]];
    const topo=[]; const vis=new Set();
    const dfs=n=>{ if(!vis.has(n)){ vis.add(n); n._p.forEach(dfs); topo.push(n); } };
    dfs(this);
    for(const n of topo.reverse()) n._b();
  }

  val() { return this.d[0][0]; }
}

// ── Linear Layer ─────────────────────────────────────────────
class Linear {
  constructor(i,o) {
    this.W=T.randn(i,o,Math.sqrt(2/i));
    this.b=new T([new Array(o).fill(0)],true);
    this.b.g=[new Array(o).fill(0)];
    this.params=[this.W,this.b];
  }
  fwd(x) { return x.matmul(this.W).add(this.b); }
}

// ── Adam ─────────────────────────────────────────────────────
class Adam {
  constructor(params,lr=0.01,b1=0.9,b2=0.999,eps=1e-8) {
    this.p=params; this.lr=lr; this.b1=b1; this.b2=b2; this.eps=eps; this.t=0;
    this.m=params.map(p=>p.d.map(r=>r.map(()=>0)));
    this.v=params.map(p=>p.d.map(r=>r.map(()=>0)));
  }
  step() {
    const {b1,b2,lr,eps} = this;
    this.t++;
    const c1=1-b1**this.t, c2=1-b2**this.t;
    this.p.forEach((p,pi)=>{
      p.g?.forEach((r,i)=>r.forEach((g,j)=>{
        this.m[pi][i][j]=b1*this.m[pi][i][j]+(1-b1)*g;
        this.v[pi][i][j]=b2*this.v[pi][i][j]+(1-b2)*g*g;
        p.d[i][j]-=lr*(this.m[pi][i][j]/c1)/(Math.sqrt(this.v[pi][i][j]/c2)+eps);
      }));
    });
  }
  zero() { this.p.forEach(p=>{ if(p.g) p.g=p.g.map(r=>r.map(()=>0)); }); }
}

// ── Train XOR ────────────────────────────────────────────────
const l1=new Linear(2,8), l2=new Linear(8,1);
const params=[...l1.params,...l2.params];
const opt=new Adam(params,0.05);

const X=new T([[0,0],[0,1],[1,0],[1,1]]);
const Y=new T([[0],[1],[1],[0]]);

for(let e=0;e<2000;e++){
  opt.zero();
  const out=l2.fwd(l1.fwd(X).relu()).sigmoid();
  const loss=out.mseLoss(Y);
  loss.backward();
  opt.step();
  if(e%500===0) console.log(`epoch ${e}: loss=${loss.val().toFixed(6)}`);
}

const pred=l2.fwd(l1.fwd(X).relu()).sigmoid();
console.log("XOR predictions:",pred.d.map(r=>r[0].toFixed(3)));
// Should be close to [0, 1, 1, 0]
```

---
## ENTRY 005 — Merkle Tree + Sparse Merkle Tree

### PROMPT
```
สร้าง Merkle Tree: build, proof generation, verify, diff สำหรับ distributed sync
และ Sparse Merkle Tree: inclusion/exclusion proofs, key-value store
```

### [Thinking & Logic]

**Standard Merkle Tree:**
```
Leaves: hash(data_i)
Parents: hash(left || right)
Proof of leaf i: siblings along path to root (O(log n) hashes)
Verify: recompute root from leaf + proof → compare
```

**Diff Algorithm:**
```
A.root == B.root → identical (O(1) check!)
else DFS: if A.child == B.child → skip subtree
→ O(k·log n) where k = changed leaves
```

**Sparse Merkle Tree (2^256 address space):**
```
key → hash(key) → path of bits → leaf position
Empty leaf: H(0)
Empty subtree at depth d: precomputed emptyHashes[d]
→ O(1) space for empty regions (structural sharing)
Proof: 256 sibling hashes along path
```

### [Implementation]

```javascript
// merkle.js
import { createHash } from "crypto";

const H  = (...args)=>createHash("sha256").update(args.join("")).digest("hex");
const H2 = (a,b)=>H(a,b);

// ── Standard Merkle Tree ──────────────────────────────────────
export class MerkleTree {
  constructor(leaves) {
    if(!leaves.length) throw new Error("need leaves");
    this.leaves  = leaves;
    this.hLeaves = leaves.map(l=>H(JSON.stringify(l)));
    this.tree    = this._build([...this.hLeaves]);
    this.root    = this.tree.at(-1)[0];
  }

  _build(level) {
    while(level.length&(level.length-1)) level.push(level.at(-1)); // pad to 2^n
    const tree=[level];
    while(level.length>1){
      const next=[];
      for(let i=0;i<level.length;i+=2) next.push(H2(level[i],level[i+1]));
      tree.push(next); level=next;
    }
    return tree;
  }

  proof(idx) {
    const p=[]; let i=idx;
    for(let d=0;d<this.tree.length-1;d++){
      const sib = i%2===0 ? i+1 : i-1;
      p.push({ h:this.tree[d][sib]??this.tree[d][i], pos:i%2===0?"R":"L" });
      i=Math.floor(i/2);
    }
    return { leaf:this.hLeaves[idx], idx, proof:p, root:this.root };
  }

  static verify({leaf,proof,root}) {
    let h=leaf;
    for(const {h:sib,pos} of proof) h=pos==="R"?H2(h,sib):H2(sib,h);
    return h===root;
  }

  static diff(A,B) {
    if(A.root===B.root) return [];
    const changed=[];
    const dfs=(d,i)=>{
      const aH=A.tree[d]?.[i], bH=B.tree[d]?.[i];
      if(aH===bH) return;
      if(d===0){ changed.push({idx:i,before:A.leaves[i],after:B.leaves[i]}); return; }
      dfs(d-1,i*2); dfs(d-1,i*2+1);
    };
    dfs(A.tree.length-2,0);
    return changed;
  }

  update(idx,newLeaf) {
    const n=[...this.leaves]; n[idx]=newLeaf; return new MerkleTree(n);
  }
}

// ── Sparse Merkle Tree ────────────────────────────────────────
export class SparseMerkle {
  constructor(depth=16) {
    this.depth  = depth;
    this.leaves = new Map(); // key → value
    this.nodes  = new Map(); // path-string → hash
    // Pre-compute empty hashes bottom-up
    this.empty  = [H("empty_leaf")];
    for(let i=0;i<depth;i++) this.empty.push(H2(this.empty[i],this.empty[i]));
  }

  get root() { return this.nodes.get("")||this.empty[this.depth]; }

  set(key,val) {
    this.leaves.set(key,val);
    this._update(this._keyBits(key), val===null?null:H(JSON.stringify(val)), 0, "");
  }

  delete(key) { this.set(key,null); }

  _update(bits,leafH,d,path) {
    if(d===this.depth){
      if(leafH) this.nodes.set(path,leafH);
      else       this.nodes.delete(path);
      return leafH||this.empty[0];
    }
    const b=bits[d], sib=path+(b==="0"?"1":"0");
    const childH=this._update(bits,leafH,d+1,path+b);
    const sibH  =this.nodes.get(sib)||this.empty[this.depth-d-1];
    const nodeH =b==="0"?H2(childH,sibH):H2(sibH,childH);
    if(nodeH!==this.empty[this.depth-d]) this.nodes.set(path,nodeH);
    else this.nodes.delete(path);
    return nodeH;
  }

  proof(key) {
    const bits=this._keyBits(key);
    const sibs=[];
    let path="";
    for(let d=0;d<this.depth;d++){
      const b=bits[d], sibPath=path+(b==="0"?"1":"0");
      sibs.push(this.nodes.get(sibPath)||this.empty[this.depth-d-1]);
      path+=b;
    }
    const val=this.leaves.get(key);
    return { key, val, leafH:val!==null&&val!==undefined?H(JSON.stringify(val)):this.empty[0], sibs, root:this.root };
  }

  static verify({leafH,sibs,root}, keyBits) {
    let h=leafH;
    for(let i=sibs.length-1;i>=0;i--){
      const b=keyBits[sibs.length-1-i];
      h=b==="0"?H2(h,sibs[i]):H2(sibs[i],h);
    }
    return h===root;
  }

  _keyBits(key) {
    const h=H(key);
    return h.split("").slice(0,this.depth).map(c=>(parseInt(c,16)>>3)&1?"1":"0").join("")
      .padEnd(this.depth,"0").slice(0,this.depth);
  }
}

// Usage
const tree=new MerkleTree(["Alice:100","Bob:200","Charlie:300","Dave:400"]);
const proof=tree.proof(1); // Bob
console.log("Valid proof:", MerkleTree.verify(proof));

const tree2=tree.update(1,"Bob:150");
console.log("Diff:", MerkleTree.diff(tree,tree2));

const smt=new SparseMerkle(16);
smt.set("user:1",{balance:1000});
smt.set("user:2",{balance:500});
const p=smt.proof("user:1");
console.log("SMT proof valid:", SparseMerkle.verify(p, smt._keyBits("user:1")));
```

---
## ENTRY 006 — HyperLogLog++ Cardinality Estimation

### PROMPT
```
สร้าง HyperLogLog++ สำหรับ approximate distinct count ด้วย fixed memory
พร้อม bias correction, sparse mode, merge operation
```

### [Thinking & Logic]

**Core Idea:**
```
hash(x) → binary string
P(ρ leading zeros) = 1/2^ρ → if we see ρ zeros, ~2^ρ items passed
m registers: bucket = first b bits of hash
ρ = count leading zeros in remaining bits
M[bucket] = max(M[bucket], ρ)
estimate = αm · m² / Σ(2^-M[j])
```

**Corrections:**
```
Small range (E < 2.5m):  Linear Counting → m·ln(m/V) where V=empty registers
Large range (E > 2^32/30): -2^32·ln(1 - E/2^32)
Sparse mode: track exact hashes until > 6m elements → switch to dense
```

**Merge:** merged.M[i] = max(A.M[i], B.M[i]) → Union cardinality
**Error:** ±1.04/√m   (m=4096 → ±1.6%, uses only 4KB!)

### [Implementation]

```javascript
// hll.js
import { createHash } from "crypto";

function mhash(key) {
  const b=Buffer.from(typeof key==="string"?key:JSON.stringify(key));
  let h=0x811c9dc5>>>0;
  for(const c of b){ h^=c; h=Math.imul(h,0x01000193)>>>0; }
  return h;
}

function rho(x) {  // leading zeros count
  if(!x) return 33;
  let c=1; while(!(x&0x80000000)){ c++; x<<=1; } return c;
}

function alpha(m) {
  if(m===16) return 0.673; if(m===32) return 0.697; if(m===64) return 0.709;
  return 0.7213/(1+1.079/m);
}

export class HLL {
  constructor(b=12) {
    if(b<4||b>16) throw Error("b must be 4-16");
    this.b=b; this.m=1<<b;
    this.M=new Uint8Array(this.m);
    this._a=alpha(this.m);
    this.sparse=new Set();
    this.isDense=false;
    this.SPARSE_MAX=this.m*6;
  }

  add(item) {
    const h=mhash(item);
    if(!this.isDense){
      this.sparse.add(h);
      if(this.sparse.size>this.SPARSE_MAX) this._toDense();
      return;
    }
    const j=h>>>(32-this.b);
    const w=(h<<this.b)|((1<<this.b)-1);
    const r=rho(w);
    if(r>this.M[j]) this.M[j]=r;
  }

  _toDense() {
    this.isDense=true;
    for(const h of this.sparse){
      const j=h>>>(32-this.b);
      const w=(h<<this.b)|((1<<this.b)-1);
      const r=rho(w);
      if(r>this.M[j]) this.M[j]=r;
    }
    this.sparse.clear();
  }

  count() {
    if(!this.isDense) return this.sparse.size;
    let sum=0,zeros=0;
    for(const v of this.M){ sum+=2**-v; if(!v) zeros++; }
    let E=this._a*this.m*this.m/sum;
    if(E<=2.5*this.m&&zeros>0) return Math.round(this.m*Math.log(this.m/zeros));
    const T32=2**32;
    if(E>T32/30) return Math.round(-T32*Math.log(1-E/T32));
    return Math.round(E);
  }

  merge(other) {
    if(this.b!==other.b) throw Error("incompatible precision");
    const r=new HLL(this.b);
    if(!this.isDense)   this._toDense();
    if(!other.isDense)  other._toDense();
    r.isDense=true;
    for(let i=0;i<this.m;i++) r.M[i]=Math.max(this.M[i],other.M[i]);
    return r;
  }

  get error() { return 1.04/Math.sqrt(this.m); }
  get memKB()  { return (this.isDense?this.m:this.sparse.size*4)/1024; }

  serialize() {
    return { b:this.b, isDense:this.isDense,
             M:this.isDense?[...this.M]:null,
             sparse:this.isDense?null:[...this.sparse] };
  }

  static from(obj) {
    const h=new HLL(obj.b);
    h.isDense=obj.isDense;
    if(obj.isDense) h.M=new Uint8Array(obj.M);
    else h.sparse=new Set(obj.sparse);
    return h;
  }
}

// Usage: count unique IPs from 1M requests
const hll=new HLL(12);
const real=new Set();
for(let i=0;i<1_000_000;i++){
  const ip=`${(i*2654435761)%256}.${(i*1234567)%256}.${i%256}.${(i/256|0)%256}`;
  hll.add(ip); real.add(ip);
}
const est=hll.count(), truth=real.size;
console.log(`Truth: ${truth.toLocaleString()}`);
console.log(`HLL:   ${est.toLocaleString()}`);
console.log(`Error: ${(Math.abs(est-truth)/truth*100).toFixed(2)}% (max ~${(hll.error*100).toFixed(2)}%)`);
console.log(`Mem:   ${hll.memKB.toFixed(2)}KB vs Set: ${real.size*50/1024|0}KB`);
```

---
## ENTRY 007 — Persistent Segment Tree (Range Query + Versioning)

### PROMPT
```
สร้าง Persistent Segment Tree: Range Sum Query, Point Update สร้าง new version
ทุก version ยังใช้ query ได้ผ่าน structural sharing, Kth smallest in range
```

### [Thinking & Logic]

**Persistent Update (Path Copying):**
```
Update position i → create O(log n) new nodes along path root→leaf
Other nodes shared with previous version → O(log n) extra memory per update

Version history: roots = [v0_root, v1_root, v2_root, ...]
Query version k → query(roots[k], ...)
```

**Kth Smallest in range [l,r]:**
```
Build version i = frequency tree after inserting first i elements
count in [l,r] = diff between version r and version l-1
→ merge sort tree / offline range kth smallest
```

**Lazy Propagation:**
```
Range add [ql,qr] delta → mark internal node with lazy tag
push down lazy ตอน query/update children
→ Range update O(log n)
```

### [Implementation]

```javascript
// pst.js

class Node {
  constructor(l=null,r=null,v=0,lazy=0,cnt=0) {
    this.l=l; this.r=r; this.v=v; this.lazy=lazy; this.cnt=cnt;
  }
}

export class PST {
  constructor(arr, mode="sum") {
    this.mode=mode; this.n=arr.length;
    this.roots=[this._build(arr,0,this.n-1)];
    this._nc=0;
  }

  _build(arr,l,r) {
    const n=new Node(); n.cnt=r-l+1;
    if(l===r){ n.v=arr[l]; return n; }
    const m=(l+r)>>1;
    n.l=this._build(arr,l,m); n.r=this._build(arr,m+1,r);
    n.v=this._cmb(n.l.v,n.r.v); return n;
  }

  _cmb(a,b) {
    return this.mode==="sum"?a+b:this.mode==="min"?Math.min(a,b):Math.max(a,b);
  }
  _id() { return this.mode==="sum"?0:this.mode==="min"?Infinity:-Infinity; }

  // ── Point Update → new version ────────────────────────────
  update(idx,val,ver=this.roots.length-1) {
    const root=this._upd(this.roots[ver],0,this.n-1,idx,val);
    this.roots.push(root);
    return this.roots.length-1;
  }

  _upd(nd,l,r,idx,val) {
    const n=new Node(nd.l,nd.r,nd.v,nd.lazy,nd.cnt);
    if(l===r){ n.v=val; return n; }
    const m=(l+r)>>1;
    if(idx<=m) n.l=this._upd(nd.l,l,m,idx,val);
    else       n.r=this._upd(nd.r,m+1,r,idx,val);
    n.v=this._cmb(n.l?.v??this._id(),n.r?.v??this._id());
    return n;
  }

  // ── Range Add with Lazy Propagation → new version ─────────
  rangeAdd(ql,qr,delta,ver=this.roots.length-1) {
    const root=this._radd(this.roots[ver],0,this.n-1,ql,qr,delta);
    this.roots.push(root);
    return this.roots.length-1;
  }

  _radd(nd,l,r,ql,qr,d) {
    if(!nd||ql>r||qr<l) return nd;
    const n=new Node(nd.l,nd.r,nd.v,nd.lazy,nd.cnt);
    if(ql<=l&&r<=qr){ n.v+=d*n.cnt; n.lazy+=d; return n; }
    this._push(n,l,r);
    const m=(l+r)>>1;
    n.l=this._radd(n.l,l,m,ql,qr,d);
    n.r=this._radd(n.r,m+1,r,ql,qr,d);
    n.v=this._cmb(n.l?.v??this._id(),n.r?.v??this._id());
    return n;
  }

  _push(n,l,r) {
    if(!n.lazy) return;
    const m=(l+r)>>1;
    const mk=(child,lc,rc)=>{
      const x=new Node(child.l,child.r,child.v+n.lazy*child.cnt,child.lazy+n.lazy,child.cnt);
      return x;
    };
    if(n.l) n.l=mk(n.l,l,(l+r)>>1);
    if(n.r) n.r=mk(n.r,(l+r>>1)+1,r);
    n.lazy=0;
  }

  // ── Range Query ───────────────────────────────────────────
  query(ql,qr,ver=this.roots.length-1) {
    return this._qry(this.roots[ver],0,this.n-1,ql,qr);
  }

  _qry(nd,l,r,ql,qr) {
    if(!nd||ql>r||qr<l) return this._id();
    if(ql<=l&&r<=qr) return nd.v;
    if(nd.lazy) this._push(nd,l,r);
    const m=(l+r)>>1;
    return this._cmb(this._qry(nd.l,l,m,ql,qr),this._qry(nd.r,m+1,r,ql,qr));
  }

  get versions() { return this.roots.length; }
}

// ── Persistent Frequency Tree for Kth Smallest ───────────────
export class KthPST {
  // Build one PST version per prefix: roots[i] = frequency of values after i insertions
  constructor(arr, minVal=0, maxVal=1000) {
    this.min=minVal; this.max=maxVal;
    this.roots=[this._build(minVal,maxVal)]; // empty
    for(const v of arr) {
      const root=this._add(this.roots.at(-1),minVal,maxVal,v);
      this.roots.push(root);
    }
  }

  _build(l,r) { const n=new Node(); n.cnt=0; if(l===r) return n; const m=(l+r)>>1; n.l=this._build(l,m); n.r=this._build(m+1,r); return n; }

  _add(nd,l,r,val) {
    const n=new Node(nd.l,nd.r,nd.v+1,0,nd.cnt+1);
    if(l===r) return n;
    const m=(l+r)>>1;
    if(val<=m) n.l=this._add(nd.l,l,m,val); else n.r=this._add(nd.r,m+1,r,val);
    return n;
  }

  // kth smallest in original array[ql..qr] (1-indexed)
  kth(ql,qr,k) {
    return this._kth(this.roots[ql-1],this.roots[qr],this.min,this.max,k);
  }

  _kth(lnd,rnd,l,r,k) {
    if(l===r) return l;
    const leftCnt=(rnd.l?.cnt??0)-(lnd.l?.cnt??0);
    const m=(l+r)>>1;
    if(k<=leftCnt) return this._kth(lnd.l,rnd.l,l,m,k);
    return this._kth(lnd.r,rnd.r,m+1,r,k-leftCnt);
  }
}

// Usage
const arr=[3,1,4,1,5,9,2,6,5,3];
const pst=new PST(arr,"sum");
console.log("Sum[2..7]:", pst.query(2,7));         // v0
const v1=pst.update(3,100);                          // arr[3]=100
console.log("Sum[2..7] v1:", pst.query(2,7,v1));   // updated
console.log("Sum[2..7] v0:", pst.query(2,7,0));    // original unchanged

const v2=pst.rangeAdd(1,5,10);
console.log("Sum[0..9] after +10 on [1..5]:", pst.query(0,9,v2));

// Kth smallest
const kpst=new KthPST([3,1,4,1,5,9,2,6,5,3],1,9);
console.log("2nd smallest in arr[2..6]:", kpst.kth(2,6,2)); // should be 1
```

---
## ENTRY 008 — Rope Data Structure (O(log n) String Ops)

### PROMPT
```
สร้าง Rope: O(log n) concat/split/index/insert/delete สำหรับ text editor
Persistent (immutable) เพื่อ undo/redo
```

### [Thinking & Logic]

**Rope vs String:**
```
String concat O(n): copy both strings
Rope concat O(1):   new InternalNode(a, b)  ← just a pointer!
Rope index O(log n): walk tree using weight (chars in left subtree)
```

**Node Types:**
```
Leaf:     { text, len }
Internal: { left, right, weight=left.len, len=left.len+right.len, height }
```

**Split(i):** walk tree splitting at position i → 2 subtrees
**Balance:** Fibonacci rebalance when height > 1.44·log₂(n+2)

### [Implementation]

```javascript
// rope.js
const LEAF_MAX=512;

class Leaf   { constructor(t){ this.t=t; this.len=t.length; this.h=0; } }
class Branch { constructor(l,r){ this.l=l; this.r=r; this.len=l.len+r.len; this.h=1+Math.max(l.h,r.h); } }

export class Rope {
  constructor(root=null){ this._root=root; }
  get length(){ return this._root?.len??0; }

  static from(s) {
    if(!s.length) return new Rope();
    const build=(s)=>{
      if(s.length<=LEAF_MAX) return new Leaf(s);
      const m=s.length>>1;
      return new Branch(build(s.slice(0,m)),build(s.slice(m)));
    };
    return new Rope(build(s));
  }

  charAt(i) {
    if(i<0||i>=this.length) throw RangeError(i);
    return this._charAt(this._root,i);
  }
  _charAt(n,i) {
    if(n instanceof Leaf) return n.t[i];
    const w=n.l.len;
    return i<w ? this._charAt(n.l,i) : this._charAt(n.r,i-w);
  }

  toString(){ return this._collect(this._root); }
  _collect(n){ return !n?"":n instanceof Leaf?n.t:this._collect(n.l)+this._collect(n.r); }

  // ── O(1) concat ──────────────────────────────────────────
  concat(other) {
    if(!this.length) return other;
    if(!other.length) return this;
    return new Rope(new Branch(this._root,other._root))._bal();
  }

  // ── O(log n) split ───────────────────────────────────────
  split(i) {
    if(i<=0) return [new Rope(),this];
    if(i>=this.length) return [this,new Rope()];
    const [l,r]=this._split(this._root,i);
    return [new Rope(l)._bal(),new Rope(r)._bal()];
  }
  _split(n,i) {
    if(!n) return [null,null];
    if(n instanceof Leaf){
      if(i<=0) return [null,n];
      if(i>=n.len) return [n,null];
      return [new Leaf(n.t.slice(0,i)),new Leaf(n.t.slice(i))];
    }
    const w=n.l.len;
    if(i===w) return [n.l,n.r];
    if(i<w){
      const [ll,lr]=this._split(n.l,i);
      return [ll,lr?new Branch(lr,n.r):n.r];
    }
    const [rl,rr]=this._split(n.r,i-w);
    return [rl?new Branch(n.l,rl):n.l,rr];
  }

  // ── Insert / Delete ───────────────────────────────────────
  insert(i,s) {
    const [l,r]=this.split(i);
    return l.concat(Rope.from(s)).concat(r);
  }
  delete(l,r) {
    const [left,rest]=this.split(l);
    const [,right]=rest.split(r-l);
    return left.concat(right);
  }
  replace(l,r,s) { return this.delete(l,r).insert(l,s); }

  // ── Rebalance (Fibonacci condition) ──────────────────────
  _bal() {
    const h=this._root?.h??0;
    const max=Math.ceil(1.44*Math.log2(this.length+2));
    if(h>max+2){
      const leaves=[];
      const collect=n=>{ if(!n) return; if(n instanceof Leaf){leaves.push(n);return;} collect(n.l);collect(n.r); };
      collect(this._root);
      const build=(ls,s,e)=>{
        if(e-s===0) return null;
        if(e-s===1) return ls[s];
        const m=(s+e)>>1;
        const l=build(ls,s,m),r=build(ls,m,e);
        return l&&r?new Branch(l,r):(l||r);
      };
      return new Rope(build(leaves,0,leaves.length));
    }
    return this;
  }

  indexOf(pat,from=0) {
    const t=this.toString().indexOf(pat,from);
    return t;
  }

  stats() {
    let leaves=0,maxH=0;
    const dfs=n=>{if(!n)return;if(n instanceof Leaf){leaves++;return;}maxH=Math.max(maxH,n.h);dfs(n.l);dfs(n.r);};
    dfs(this._root);
    return {length:this.length,height:this._root?.h??0,leaves,balanced:this._root?.h??0<=Math.ceil(1.44*Math.log2(this.length+2))};
  }
}

// ── Persistent Text Editor ────────────────────────────────────
export class Editor {
  constructor(s=""){ this._h=[Rope.from(s)]; this._i=0; }
  get text(){ return this._h[this._i].toString(); }
  _commit(r){ this._h=this._h.slice(0,this._i+1); this._h.push(r); this._i++; }
  insert(pos,s){ this._commit(this._h[this._i].insert(pos,s)); }
  delete(l,r)  { this._commit(this._h[this._i].delete(l,r)); }
  replace(l,r,s){ this._commit(this._h[this._i].replace(l,r,s)); }
  undo(){ if(this._i>0) this._i--; }
  redo(){ if(this._i<this._h.length-1) this._i++; }
  get canUndo(){ return this._i>0; }
  get canRedo(){ return this._i<this._h.length-1; }
}

// Usage
const ed=new Editor("Hello World");
ed.insert(5," Beautiful");
console.log(ed.text); // Hello Beautiful World
ed.delete(5,15);
console.log(ed.text); // Hello World
ed.undo();
console.log(ed.text); // Hello Beautiful World
ed.redo();

// Performance test
let r=Rope.from("a".repeat(100000));
const t=Date.now();
for(let i=0;i<1000;i++) r=r.insert(50000,"X");
console.log(`1000 inserts in ${Date.now()-t}ms, stats:`, r.stats());
```

---
## ENTRY 009 — Custom DNS Resolver (UDP Wire Format + Cache)

### PROMPT
```
สร้าง DNS Resolver: parse DNS wire format (RFC 1035), recursive query,
TTL-aware cache, parallel A+AAAA, RTT-based server selection
```

### [Thinking & Logic]

**DNS Wire Format:**
```
Header: ID(2) FLAGS(2) QDCOUNT ANCOUNT NSCOUNT ARCOUNT (each 2 bytes)
Question: QNAME(labels) QTYPE(2) QCLASS(2)
RR: NAME TYPE(2) CLASS(2) TTL(4) RDLEN(2) RDATA

Label encoding: \x03www\x07example\x03com\x00
Name compression: 0xC0XX → pointer to offset XX
```

**Query Algorithm:**
```
1. Check cache (TTL-aware)
2. Select best server (lowest EWMA RTT)
3. Send UDP query with timeout
4. Parse response → cache → return
5. Follow CNAME chain if needed
```

### [Implementation]

```javascript
// dns.js
import dgram from "dgram";

const TYPE = {A:1,NS:2,CNAME:5,MX:15,AAAA:28,TXT:16};
const RC   = {0:"NOERROR",3:"NXDOMAIN",5:"REFUSED"};

// ── DNS Message Builder ───────────────────────────────────────
function buildQuery(id,name,type) {
  const b=Buffer.alloc(512); let o=0;
  b.writeUInt16BE(id,o);o+=2;
  b.writeUInt16BE(0x0100,o);o+=2; // RD=1
  b.writeUInt16BE(1,o);o+=2;      // QDCOUNT=1
  b.writeUInt16BE(0,o);o+=2; b.writeUInt16BE(0,o);o+=2; b.writeUInt16BE(0,o);o+=2;
  for(const label of name.split(".").filter(Boolean)){
    b[o++]=label.length; b.write(label,o,"ascii"); o+=label.length;
  }
  b[o++]=0;
  b.writeUInt16BE(type,o);o+=2; b.writeUInt16BE(1,o);o+=2;
  return b.slice(0,o);
}

// ── DNS Message Parser ────────────────────────────────────────
function parseName(b,off) {
  const parts=[]; let jumped=false,orig=off;
  while(true){
    const len=b[off];
    if(!len){ off++; break; }
    if((len&0xC0)===0xC0){
      if(!jumped) orig=off+2;
      off=((len&0x3F)<<8)|b[off+1]; jumped=true; continue;
    }
    off++;
    parts.push(b.slice(off,off+len).toString("ascii"));
    off+=len;
  }
  return [parts.join("."),jumped?orig:off];
}

function parseRData(b,off,type,rdLen) {
  switch(type){
    case TYPE.A:     return {ip:[...b.slice(off,off+4)].join(".")};
    case TYPE.AAAA: {
      const ps=[]; for(let i=0;i<16;i+=2) ps.push(b.readUInt16BE(off+i).toString(16));
      return {ip:ps.join(":")};
    }
    case TYPE.CNAME: case TYPE.NS: case TYPE.MX: {
      const pref=type===TYPE.MX?b.readUInt16BE(off):0;
      const [n]=parseName(b,type===TYPE.MX?off+2:off);
      return type===TYPE.MX?{pref,exchange:n}:{name:n};
    }
    case TYPE.TXT: {
      const txts=[]; let p=off;
      while(p<off+rdLen){ const l=b[p++]; txts.push(b.slice(p,p+l).toString()); p+=l; }
      return {txts};
    }
    default: return {raw:b.slice(off,off+rdLen)};
  }
}

function parseMsg(b) {
  const id=b.readUInt16BE(0),flags=b.readUInt16BE(2);
  const qd=b.readUInt16BE(4),an=b.readUInt16BE(6),ns=b.readUInt16BE(8),ar=b.readUInt16BE(10);
  const msg={id,rcode:flags&0xF,rd:(flags>>8)&1,ra:(flags>>7)&1,questions:[],answers:[],authority:[],additional:[]};
  let o=12;
  for(let i=0;i<qd;i++){
    const [name,no]=parseName(b,o); o=no;
    msg.questions.push({name,type:b.readUInt16BE(o),cls:b.readUInt16BE(o+2)}); o+=4;
  }
  const parseRRs=(cnt)=>{
    const rrs=[];
    for(let i=0;i<cnt;i++){
      const [name,no]=parseName(b,o); o=no;
      const type=b.readUInt16BE(o),cls=b.readUInt16BE(o+2),ttl=b.readUInt32BE(o+4),rdLen=b.readUInt16BE(o+8);
      o+=10;
      rrs.push({name,type,cls,ttl,rdata:parseRData(b,o,type,rdLen)}); o+=rdLen;
    }
    return rrs;
  };
  msg.answers=parseRRs(an); msg.authority=parseRRs(ns); msg.additional=parseRRs(ar);
  return msg;
}

// ── DNS Cache ─────────────────────────────────────────────────
class DNSCache {
  constructor(){ this.c=new Map(); }
  key(n,t){ return `${n.toLowerCase()}:${t}`; }
  set(n,t,rrs,ttl){
    this.c.set(this.key(n,t),{rrs,exp:Date.now()+ttl*1000});
  }
  get(n,t){
    const e=this.c.get(this.key(n,t));
    if(!e) return null;
    if(Date.now()>e.exp){ this.c.delete(this.key(n,t)); return null; }
    const rem=Math.floor((e.exp-Date.now())/1000);
    return e.rrs.map(r=>({...r,ttl:rem}));
  }
}

// ── Resolver ──────────────────────────────────────────────────
export class DNSResolver {
  constructor(servers=["8.8.8.8","1.1.1.1"],opts={}) {
    this.servers=servers; this.timeout=opts.timeout||3000;
    this.retries=opts.retries||2; this.cache=new DNSCache();
    this._id=1; this._sock=null; this._pending=new Map();
    this._rtt=new Map();
  }

  async init() {
    this._sock=dgram.createSocket("udp4");
    this._sock.on("message",(b)=>{
      const r=parseMsg(b);
      const p=this._pending.get(r.id);
      if(p){ clearTimeout(p.timer); this._pending.delete(r.id); p.res(r); }
    });
    await new Promise(res=>this._sock.bind(0,res));
  }

  async resolve(name,type=TYPE.A) {
    name=name.toLowerCase().replace(/\.$/,"");
    const cached=this.cache.get(name,type);
    if(cached) return cached;

    const srv=this._bestServer();
    for(let a=0;a<=this.retries;a++){
      try{
        const t0=Date.now();
        const id=(this._id=(this._id+1)%65535);
        const resp=await Promise.race([
          new Promise((res,rej)=>{
            const timer=setTimeout(()=>{this._pending.delete(id);rej(new Error("timeout"));},this.timeout);
            this._pending.set(id,{res,rej,timer});
            this._sock.send(buildQuery(id,name,type),53,srv);
          }),
        ]);
        const rtt=Date.now()-t0;
        this._rtt.set(srv,(this._rtt.get(srv)??rtt)*0.875+rtt*0.125);

        if(resp.rcode===3) throw Object.assign(new Error("NXDOMAIN"),{code:3});
        if(resp.rcode!==0) throw new Error(RC[resp.rcode]||`rcode=${resp.rcode}`);

        // Follow CNAME
        const cname=resp.answers.find(r=>r.type===TYPE.CNAME);
        if(cname&&type!==TYPE.CNAME) return this.resolve(cname.rdata.name,type);

        const ans=resp.answers;
        if(ans.length) this.cache.set(name,type,ans,Math.min(...ans.map(r=>r.ttl)));
        return ans;
      } catch(e){
        if(a===this.retries||e.code===3) throw e;
        await new Promise(r=>setTimeout(r,200*(a+1)));
      }
    }
  }

  async resolveAll(name) {
    const [a,b]=await Promise.allSettled([this.resolve(name,TYPE.A),this.resolve(name,TYPE.AAAA)]);
    return { A:a.status==="fulfilled"?a.value:[], AAAA:b.status==="fulfilled"?b.value:[] };
  }

  _bestServer() {
    return this.servers.reduce((best,s)=>{
      return (this._rtt.get(s)??Infinity)<(this._rtt.get(best)??Infinity)?s:best;
    });
  }

  close(){ this._sock?.close(); }
}

// Usage
const r=new DNSResolver(["8.8.8.8","1.1.1.1"],{timeout:3000});
await r.init();
try{
  const all=await r.resolveAll("example.com");
  console.log("IPv4:",all.A.map(x=>x.rdata.ip));
  console.log("IPv6:",all.AAAA.map(x=>x.rdata.ip));
  // Second call: from cache
  const cached=await r.resolve("example.com",TYPE.A);
  console.log("Cached TTL:",cached[0]?.ttl);
}finally{ r.close(); }
```

---
## ENTRY 010 — Two-Phase Locking + Deadlock Detection

### PROMPT
```
สร้าง Lock Manager: S/X locks, 2PL, Wait-For Graph, deadlock detection + resolution
```

### [Thinking & Logic]

**Compatibility Matrix:**
```
       S    X
  S    ✓    ✗
  X    ✗    ✗
```

**Wait-For Graph:**
```
T1 → T2 = "T1 waits for T2 to release lock"
Cycle = Deadlock → kill youngest transaction (youngest = started most recently)
Detection: DFS cycle detection O(V+E)
```

**2PL:**
```
Growing phase:  can ACQUIRE, cannot release
Shrinking phase: can RELEASE, cannot acquire
Strict 2PL: release ALL locks at commit → no cascading abort
```

### [Implementation]

```javascript
// lockmanager.js
import { EventEmitter } from "events";

const L={S:"S",X:"X"};
const COMPAT={S:{S:true,X:false},X:{S:false,X:false}};

class LockReq {
  constructor(tx,mode){
    this.tx=tx; this.mode=mode; this.granted=false;
    this.p=new Promise((res,rej)=>{ this.res=res; this.rej=rej; });
    this.ts=Date.now();
  }
}

export class LockManager extends EventEmitter {
  constructor(opts={}){
    super();
    this.locks   = new Map();  // resource → {granted:[], waiting:[]}
    this.txLocks = new Map();  // tx → Set<resource>
    this.wfg     = new Map();  // tx → Set<tx> (wait-for)
    this.txTs    = new Map();  // tx → start time
    this.timeout = opts.timeout||5000;
    this._dd=setInterval(()=>this._detect(),opts.ddInterval||200);
  }

  // ── Lock ─────────────────────────────────────────────────
  async lock(tx,res,mode=L.S){
    if(!this.txTs.has(tx)) this.txTs.set(tx,Date.now());
    if(!this.locks.has(res)) this.locks.set(res,{granted:[],waiting:[]});
    const s=this.locks.get(res);
    const req=new LockReq(tx,mode);

    if(this._canGrant(s,req)){
      req.granted=true; s.granted.push(req);
      this._track(tx,res); return;
    }

    s.waiting.push(req);
    const holders=[...new Set(s.granted.map(r=>r.tx).filter(id=>id!==tx))];
    if(!this.wfg.has(tx)) this.wfg.set(tx,new Set());
    holders.forEach(h=>this.wfg.get(tx).add(h));

    const timer=setTimeout(()=>{
      s.waiting=s.waiting.filter(r=>r!==req);
      this.wfg.delete(tx);
      req.rej(new Error(`Lock timeout: tx=${tx} res=${res}`));
    },this.timeout);

    try{ await req.p; clearTimeout(timer); }
    catch(e){ clearTimeout(timer); throw e; }
  }

  // ── Release ───────────────────────────────────────────────
  release(tx,res){
    const s=this.locks.get(res); if(!s) return;
    s.granted=s.granted.filter(r=>r.tx!==tx);
    this._processWaiting(s,res);
    this.txLocks.get(tx)?.delete(res);
    for(const[id,ws] of this.wfg) ws.delete(tx);
  }

  releaseAll(tx){
    const rs=this.txLocks.get(tx)||new Set();
    for(const res of rs){
      const s=this.locks.get(res); if(!s) continue;
      s.granted=s.granted.filter(r=>r.tx!==tx);
      s.waiting=s.waiting.filter(r=>{ if(r.tx===tx){r.rej(new Error("Aborted"));return false;} return true; });
      this._processWaiting(s,res);
    }
    this.txLocks.delete(tx); this.txTs.delete(tx);
    for(const[,ws] of this.wfg) ws.delete(tx);
    this.wfg.delete(tx);
  }

  _canGrant(s,req){
    return s.granted.every(g=>g.tx===req.tx||COMPAT[g.mode][req.mode]);
  }

  _processWaiting(s,res){
    const grant=[];
    for(const req of s.waiting){
      const allOK=[...s.granted,...grant].every(g=>g.tx===req.tx||COMPAT[g.mode][req.mode]);
      if(allOK) grant.push(req); else break;
    }
    for(const req of grant){
      s.waiting=s.waiting.filter(r=>r!==req);
      s.granted.push(req); req.granted=true;
      this._track(req.tx,res);
      for(const[,ws] of this.wfg) ws.delete(req.tx);
      this.wfg.delete(req.tx);
      req.res();
    }
  }

  _track(tx,res){
    if(!this.txLocks.has(tx)) this.txLocks.set(tx,new Set());
    this.txLocks.get(tx).add(res);
  }

  // ── Deadlock Detection (DFS cycle) ───────────────────────
  _detect(){
    const vis=new Set(),rec=new Set();
    const cycles=[];
    const dfs=(tx,path)=>{
      vis.add(tx); rec.add(tx);
      for(const w of this.wfg.get(tx)||[]){
        if(!vis.has(w)) dfs(w,[...path,w]);
        else if(rec.has(w)){
          const ci=path.indexOf(w);
          if(ci!==-1) cycles.push(path.slice(ci));
        }
      }
      rec.delete(tx);
    };
    for(const tx of this.wfg.keys()) if(!vis.has(tx)) dfs(tx,[tx]);

    for(const cycle of cycles){
      const victim=cycle.reduce((y,tx)=>(this.txTs.get(tx)??0)>(this.txTs.get(y)??0)?tx:y);
      this.emit("deadlock",{cycle,victim});
      this.releaseAll(victim);
    }
  }

  destroy(){ clearInterval(this._dd); }
}

// Usage: simulate deadlock
const lm=new LockManager({timeout:3000,ddInterval:100});
lm.on("deadlock",({cycle,victim})=>console.log(`Deadlock [${cycle}] killed: ${victim}`));

const [T1,T2]=["T1","T2"];
await lm.lock(T1,"A",L.X); console.log("T1 got A");
await lm.lock(T2,"B",L.X); console.log("T2 got B");

const p1=lm.lock(T1,"B",L.X).then(()=>console.log("T1 got B")).catch(e=>console.log("T1 aborted:",e.message));
const p2=lm.lock(T2,"A",L.X).then(()=>console.log("T2 got A")).catch(e=>console.log("T2 aborted:",e.message));

await Promise.allSettled([p1,p2]);
lm.destroy();
```

---
## ENTRY 011 — Actor Model System (Mailbox + Supervision Tree)

### PROMPT
```
สร้าง Actor Model: mailbox, message passing, supervision tree
strategies: restart/stop/escalate, dead letter queue, graceful shutdown
```

### [Thinking & Logic]

**Actor Principles:**
```
1. Everything is an Actor
2. Actors communicate ONLY via messages (no shared memory)
3. Message processing: one at a time per actor (sequential)
4. React to message: send messages | create actors | change behavior

Supervision:
  parent supervises children
  child fails → parent strategy: restart | stop | escalate
  restart: fresh state, lost in-flight messages
```

### [Implementation]

```javascript
// actors.js
import { EventEmitter } from "events";

const Strategy={RESTART:"restart",STOP:"stop",ESCALATE:"escalate"};

class Mailbox {
  constructor(){ this._q=[]; this._running=false; this._actor=null; }
  enqueue(msg){ this._q.push(msg); this._drain(); }
  async _drain(){
    if(this._running||!this._actor?._alive) return;
    this._running=true;
    while(this._q.length&&this._actor?._alive){
      const msg=this._q.shift();
      try{ await this._actor.receive(msg.payload,msg.sender); }
      catch(e){ await this._actor._ctx?._handleFail(this._actor,e); }
    }
    this._running=false;
  }
}

export class Actor {
  constructor(){ this._alive=true; this._mb=new Mailbox(); this._mb._actor=this; this._ctx=null; this.children=new Map(); }
  receive(msg,sender){ throw new Error("override receive()"); }
  supervisorStrategy(){ return {strategy:Strategy.RESTART,maxRestarts:3,withinMs:60000}; }
  get context(){ return this._ctx; }
}

export class ActorRef {
  constructor(id,sys){ this.id=id; this._sys=sys; }
  tell(msg,sender=null){ this._sys._deliver(this.id,msg,sender); }
  async ask(msg,to=5000){
    return new Promise((res,rej)=>{
      const tmp=this._sys._tempActor(res);
      this.tell(msg,tmp);
      setTimeout(()=>{ this._sys._killTemp(tmp.id); rej(new Error("ask timeout")); },to);
    });
  }
}

export class ActorSystem extends EventEmitter {
  constructor(name="sys"){ super(); this.name=name; this._actors=new Map(); this._dl=[]; this._seq=0; }

  spawn(ActorClass,name,args=[],parentId="/"){
    const id=`${parentId}/${name}`;
    const actor=new ActorClass(...args);
    const ref=new ActorRef(id,this);
    actor._ctx={
      self:ref, system:this,
      spawn:(C,n,a)=>this.spawn(C,n,a,id),
      parent:this._actors.get(parentId)?.ref||null,
      stop:(r)=>this._stop(r.id),
      _handleFail:(a,e)=>this._handleFail(id,e),
    };
    this._actors.set(id,{actor,ref,parentId,name,ActorClass,args,restarts:[],watchers:new Set()});
    this.emit("spawned",{id,name});
    return ref;
  }

  _deliver(id,payload,sender){
    const e=this._actors.get(id);
    if(!e||!e.actor._alive){ this._dl.push({to:id,payload,sender,at:new Date()}); this.emit("dead-letter",{id,payload}); return; }
    e.actor._mb.enqueue({payload,sender});
  }

  async _handleFail(id,err){
    const e=this._actors.get(id); if(!e) return;
    this.emit("actor:error",{id,err:err.message});
    const pe=this._actors.get(e.parentId);
    const {strategy,maxRestarts,withinMs}=pe?.actor.supervisorStrategy()??{strategy:Strategy.STOP};
    const now=Date.now();
    if(strategy===Strategy.RESTART){
      e.restarts=e.restarts.filter(t=>now-t<withinMs);
      if(e.restarts.length>=maxRestarts){ this._stop(id); return; }
      e.restarts.push(now);
      const fresh=new e.ActorClass(...e.args);
      fresh._ctx=e.actor._ctx;
      fresh._ctx._handleFail=(a,er)=>this._handleFail(id,er);
      e.actor=fresh; fresh._mb._actor=fresh;
      this.emit("actor:restarted",{id});
    } else if(strategy===Strategy.STOP){
      this._stop(id);
    } else {
      await this._handleFail(e.parentId,err);
    }
  }

  _stop(id){
    const e=this._actors.get(id); if(!e) return;
    e.actor._alive=false; e.actor._mb._q=[];
    for(const[,cr] of e.actor.children) this._stop(cr.id);
    for(const wid of e.watchers) this._deliver(wid,{type:"Terminated",ref:e.ref},null);
    this._actors.delete(id);
    this.emit("actor:stopped",{id});
  }

  _tempActor(res){
    const id=`/tmp/${++this._seq}`;
    const ref=new ActorRef(id,this);
    this._actors.set(id,{
      actor:{ _alive:true, _mb:{ enqueue(m){ res(m.payload); } }, children:new Map() },
      ref, parentId:null, name:"tmp", ActorClass:null, args:[], restarts:[], watchers:new Set()
    });
    return ref;
  }
  _killTemp(id){ this._actors.delete(id); }

  terminate(){ for(const id of [...this._actors.keys()]) this._stop(id); }
}

// Usage: Ping-Pong
class Ping extends Actor {
  constructor(){ super(); this.n=0; }
  async receive(msg,sender){
    if(msg.type==="start"){ this.n=0; sender.tell({type:"ping"},this._ctx.self); }
    if(msg.type==="pong"){ this.n++; console.log(`ping #${this.n}`); if(this.n<5) sender.tell({type:"ping"},this._ctx.self); else this._ctx.system.terminate(); }
  }
}
class Pong extends Actor {
  async receive(msg,sender){ if(msg.type==="ping"){ console.log("pong"); sender.tell({type:"pong"},this._ctx.self); } }
}

const sys=new ActorSystem("demo");
const ping=sys.spawn(Ping,"ping");
const pong=sys.spawn(Pong,"pong");

// Fault tolerance demo
class Crashy extends Actor {
  async receive(msg){
    if(msg==="crash") throw new Error("intentional crash");
    console.log("Crashy got:",msg,"(survived)");
  }
}

const c=sys.spawn(Crashy,"crashy");
sys.on("actor:restarted",({id})=>console.log(`Actor ${id} restarted`));
c.tell("hello");
c.tell("crash");  // will trigger supervisor restart
setTimeout(()=>c.tell("hello again"),100); // works after restart

ping.tell({type:"start"},pong);
