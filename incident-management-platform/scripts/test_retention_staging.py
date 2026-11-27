"""Exercise the real PS 5.1 script on fictitious archives in disposable projects."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta
from uuid import uuid4

SOURCE = Path(__file__).with_name("retention_staging.ps1")
PS = str(Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe")
base = Path(tempfile.mkdtemp(prefix="incident-retention-tests-")).resolve()
passed = 0
def fixture(name):
    root = base / name
    (root / "scripts").mkdir(parents=True)
    (root / "backups/logs").mkdir(parents=True)
    shutil.copyfile(SOURCE, root / "scripts/retention_staging.ps1")
    return root
def archive(root, date, uid=None):
    uid = uid or uuid4().hex
    stamp = date.strftime("%Y-%m-%d_%H-%M-%S") + "_" + uid
    path = root / "backups" / ("staging_" + stamp + ".dump")
    data = ("FICTITIOUS ARCHIVE, NOT A POSTGRESQL BACKUP " + uid).encode()
    path.write_bytes(data)
    proof = "\n".join([
        "BEGIN environment=staging compose_project=incident-staging service=db",
        "Target verified: incident-staging/db database=incident_management_staging",
        "Archive validation: pg_restore --list OK",
        "Copy: OK; local SHA256 matches validated container archive",
        f"SUCCESS archive={path} bytes={len(data)} SHA256={hashlib.sha256(data).hexdigest().upper()}",
        "END exit_code=0 duration_seconds=1",
    ])
    proof = "\n".join("2026-01-01T00:00:00+01:00 " + line for line in proof.splitlines())
    (root / "backups/logs" / ("backup_" + stamp + ".log")).write_text(proof, encoding="utf-8")
    return path
def run(root, apply=False, plan=None, expected=0):
    args = [PS, "-NoProfile", "-NonInteractive", "-File", str(root / "scripts/retention_staging.ps1")]
    if apply: args += ["-Apply"]
    if plan: args += ["-PlanPath", str(plan)]
    result = subprocess.run(args, capture_output=True, text=True, errors="replace")
    assert result.returncode == expected, result.stdout + result.stderr
    if expected: return
    latest = max((root / "backups/logs").glob("retention_*.json"), key=lambda p: p.stat().st_mtime_ns)
    return json.loads(latest.read_text(encoding="utf-8-sig")), latest
def check(name):
    global passed
    passed += 1
    print("PASS " + name, flush=True)
def history(root):
    for i in range(40): archive(root, datetime(2025,12,1) + timedelta(days=i))
try:
    root=fixture("empty")
    p,_=run(root)
    assert not p["Decisions"]
    check("empty")
    root=fixture("single")
    newest=archive(root,datetime(2025,12,1))
    p,_=run(root,True)
    assert newest.exists() and p["Reliable"]==1
    check("single latest protected")
    root=fixture("few")
    for i in range(6): archive(root,datetime(2025,12,1)+timedelta(days=i))
    p,_=run(root,True)
    assert not p["Sufficient"] and len(list((root/"backups").glob("*.dump")))==6
    check("less than seven days")
    root=fixture("many"); history(root)
    newest=archive(root,datetime(2026,1,9,23), "f"*32)
    tie=archive(root,datetime(2026,1,9,23), "a"*32)
    p,plan=run(root)
    assert p["Daily"]==7 and p["Weekly"]==4
    assert len(list((root/"backups").glob("*.dump")))==42
    check("more than seven distinct days; simulation unchanged")
    byname={d["Name"]:d for d in p["Decisions"]}
    assert byname[newest.name]["Action"]=="KEEP" and byname[tie.name]["Action"]=="DELETE"
    check("same-day and deterministic tie")
    weekly=[d for d in p["Decisions"] if "weekly point" in d["Reason"]]
    assert len(weekly)==4 and any(d["Date"].startswith("2025-12-28") for d in weekly)
    check("Monday-Sunday across year boundary")
    keep={d["Name"] for d in p["Decisions"] if d["Action"]=="KEEP"}
    run(root,True,plan)
    assert {f.name for f in (root/"backups").glob("*.dump")}==keep
    p,_=run(root,True)
    assert not any(d["Action"]=="DELETE" for d in p["Decisions"]) and newest.exists()
    check("union apply and idempotence")
    root=fixture("unknown")
    for name in ["staging_backup.dump","development.dump","staging_2025-12-01_00-00-00.dump","staging_2025-99-01_00-00-00_"+("a"*32)+".dump","staging_any.dump.partial"]:
        (root/"backups"/name).write_text("fake")
    p,_=run(root,True)
    assert len(p["Decisions"])==5 and all(d["Action"]=="PROTECT" for d in p["Decisions"])
    check("invalid names, dates, manual, legacy and partial protected")
    root=fixture("tampered"); a=archive(root,datetime(2025,12,1))
    a.write_text("tampered")
    p,_=run(root)
    assert p["Reliable"]==0
    check("hash mismatch")
    root=fixture("stale"); history(root); p,plan=run(root)
    a=next((root/"backups").glob("*.dump")); a.write_text("changed")
    run(root,True,plan,1)
    assert len(list((root/"backups").glob("*.dump")))==40
    check("modification invalidates persisted plan")
    p,plan=run(root); (root/"backups/new.dump").write_text("new")
    run(root,True,plan,1)
    check("file addition invalidates plan")
    external=base/"outside.json"; shutil.copyfile(plan,external)
    run(root,True,external,1)
    check("outside allowed path refused")
    root=fixture("unavailable"); (root/"backups/logs").rmdir(); (root/"backups").rmdir()
    run(root,expected=1); check("unavailable directory")
    root=fixture("junction")
    (root/"backups").rename(root/"actual")
    command=f"New-Item -ItemType Junction -Path '{root / 'backups'}' -Target '{root / 'actual'}' | Out-Null"
    subprocess.run([PS,"-NoProfile","-Command",command],check=True)
    try: run(root,True,expected=1)
    finally:
        # Remove only this junction, never traverse its target.
        subprocess.run([PS,"-NoProfile","-Command",f"[IO.Directory]::Delete('{root / 'backups'}')"],check=True)
    check("root junction rejected")
    root=fixture("few-weeks")
    for i in range(10): archive(root,datetime(2025,12,1)+timedelta(days=i))
    p,_=run(root,True)
    assert not p["Sufficient"] and len(list((root/"backups").glob("*.dump")))==10
    check("seven days insufficient without four weeks")
    root=fixture("no-proof")
    a=archive(root,datetime(2025,12,1))
    next((root/"backups/logs").glob("backup_*.log")).unlink()
    p,_=run(root,True)
    assert p["Reliable"]==0 and a.exists()
    check("matching filename without proof protected")
    root=fixture("changed-proof"); history(root)
    p,plan=run(root)
    proof=next((root/"backups/logs").glob("backup_*.log"))
    proof.write_text(proof.read_text()+"\nFAILURE")
    run(root,True,plan,1)
    assert len(list((root/"backups").glob("*.dump")))==40
    check("changed evidence invalidates plan")
    root=fixture("forged-decisions"); history(root)
    a=root/"backups/manual.dump"; a.write_text("manual")
    p,plan=run(root)
    for d in p["Decisions"]: d["Action"]="DELETE"
    plan.write_text(json.dumps(p),encoding="utf-8-sig")
    run(root,True,plan)
    assert a.exists() and any((root/"backups").glob("staging_*.dump"))
    check("plan decisions recomputed instead of trusted")
    root=fixture("locked")
    lockpath=root/"backups/.backup-staging.lock"
    command=f"$h=[IO.File]::Open('{lockpath}',[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None); [Console]::WriteLine('READY'); try {{ [Console]::ReadLine() | Out-Null }} finally {{ $h.Dispose() }}"
    holder=subprocess.Popen([PS,"-NoProfile","-Command",command],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
    try:
        assert holder.stdout.readline().strip()=="READY"
        run(root,True,expected=1)
    finally:
        holder.communicate("\n",timeout=10)
    check("shared lock refuses concurrent backup or retention")
    root=fixture("directory-link")
    external=base/"external"; external.mkdir()
    marker=external/"manual.dump"; marker.write_text("untouched")
    link=root/"backups/linked"
    subprocess.run([PS,"-NoProfile","-Command",f"New-Item -ItemType Junction -Path '{link}' -Target '{external}' | Out-Null"],check=True)
    try:
        p,_=run(root,True)
        assert marker.read_text()=="untouched" and any(d["Action"]=="PROTECT" and d["Name"]=="linked" for d in p["Decisions"])
    finally:
        subprocess.run([PS,"-NoProfile","-Command",f"[IO.Directory]::Delete('{link}')"],check=True)
    check("child junction preserved without traversal")
    print(f"RESULT: {passed} scenarios passed; fictitious archives only.",flush=True)
finally:
    assert base.parent==Path(tempfile.gettempdir()).resolve() and base.name.startswith("incident-retention-tests-")
    # Do not recursively delete a fixture with unresolved links/junctions.
    for directory, dirs, files in os.walk(base, followlinks=False):
        for name in dirs+files:
            p=Path(directory)/name
            assert not p.is_symlink() and not p.is_junction(), str(p)
    shutil.rmtree(base)
