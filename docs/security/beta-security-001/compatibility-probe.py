"""Focused musl/Python compatibility probe on the official candidate's exact backend bytes."""
import hashlib, importlib.util, json, os, subprocess, sys, urllib.request, zipfile
from pathlib import Path
root=Path.cwd(); tools=Path('/tmp/beta-security-pytest');tools.mkdir(exist_ok=True)
locked={'pytest':'9.1.1','iniconfig':'2.3.0','packaging':'26.3','pluggy':'1.6.0','pygments':'2.21.0'}
evidence=[]
for name, version in locked.items():
 with urllib.request.urlopen(f'https://pypi.org/pypi/{name}/{version}/json',timeout=30) as response:
  metadata=json.load(response)
 wheel=next(f for f in metadata['urls'] if f['filename'].endswith('none-any.whl'))
 with urllib.request.urlopen(wheel['url'],timeout=30) as response:data=response.read()
 assert hashlib.sha256(data).hexdigest()==wheel['digests']['sha256']
 wheelpath=tools/wheel['filename'];wheelpath.write_bytes(data)
 with zipfile.ZipFile(wheelpath) as archive:archive.extractall(tools)
 evidence.append({'name':name,'version':version,'wheel':wheel['filename'],'sha256':wheel['digests']['sha256']})
(tools/'test-tool-inputs.json').write_text(json.dumps(evidence,indent=2)+'\n')
for path in [tools,*tools.rglob('*')]:
 path.chmod(0o755 if path.is_dir() else 0o644)
sys.path.insert(0,str(root/'scripts'))
spec=importlib.util.spec_from_file_location('candidate',root/'scripts/build-beta-candidate.py'); module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
original=module.run_artifact_smoke
from workflow_resources import Disposable,Owner

def probe(artifact,local,log=None):
 original(artifact,local,log)
 manifest=json.loads((artifact/'candidate.json').read_text());ref=manifest['images']['backend']['reference']
 owner=Owner.disposable('workflow-smoke',root)
 with Disposable(owner):
  cmd=['docker','run','--rm','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges:true','--tmpfs','/tmp:rw,noexec,nosuid,size=256m','--mount',f'type=bind,src={tools},dst=/testtools,readonly','--mount',f'type=bind,src={root}/backend,dst=/test-suite,readonly','--env','PYTHONPATH=/testtools','--env','PYTEST_DISABLE_PLUGIN_AUTOLOAD=1','--env','PYTHONDONTWRITEBYTECODE=1','--workdir','/test-suite']
  for k,v in owner.labels().items():cmd+=['--label',k+'='+v]
  selected=['tests/test_attachment_storage.py','tests/test_attachment_service.py','tests/test_external_botany_provider.py','tests/test_external_botany_service.py','tests/test_external_botany_api.py','tests/test_occurrence_cache.py','tests/test_taxonomy.py','tests/test_taxonomy_service.py','tests/test_geographic_place.py']
  code="import certifi,ssl,sys,sqlite3,platform;from importlib.metadata import version;print('RUNTIME_COMPATIBILITY',platform.libc_ver(),sys.version,sqlite3.sqlite_version,version('pillow'),version('certifi'),flush=True);ctx=ssl.create_default_context(cafile=certifi.where());assert ctx.verify_mode==ssl.CERT_REQUIRED and ctx.check_hostname;import pytest;raise SystemExit(pytest.main(['-q','-o','addopts=','-p','no:cacheprovider',*sys.argv[1:]]))"
  subprocess.run(cmd+[ref,'python','-c',code,*selected],check=True)
module.run_artifact_smoke=probe
sys.argv=['build-beta-candidate.py','--evidence','/tmp/beta-security-candidate-c.json','--security-dir','/tmp/beta-security-candidate-c-scans']
module.main()
