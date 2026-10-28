"""Runs the model on a Colab GPU via the official `google-colab-cli` (pip install google-colab-cli).

talk:      zip the repo → provision VM → start `main.py model` there → ssh -L tunnel → run talk locally with --model_url
finetune:  zip the repo → provision VM → run `main.py finetune` there → push to the Hub or download out-saturday/
"""
import os
import re
import shlex
import shutil
import ssl
import subprocess
import sys
import time

from common.constants import (ARCHIVE_EXCLUDE, ARCHIVE_MAX_MB, CA_BUNDLE_FILE, EXPORT_DIR, LOCAL_ZIP, MODEL_HOST,
                              REMOTE_ENV, REMOTE_LOG, REMOTE_OK, REMOTE_OUT_ZIP, REMOTE_PACKAGES, REMOTE_REMOVE,
                              REMOTE_ROOT, REMOTE_STARTED, REMOTE_ZIP, RETRY_DELAY, SERVER_AUTH_OID, SESSION_LINE,
                              SSH_HOST, SSH_KEYS, SSH_OPTIONS, TRANSIENT_ERRORS, UPLOAD_RETRIES)
from common.utils import port_in_use, wait_for_health, zip_dir

REMOTE_SETUP = '''
import os, shutil, subprocess, sys, time, zipfile
print({started!r}, flush=True)
os.environ.update({env!r})
root = {root!r}
shutil.rmtree(root, ignore_errors=True)
for stale in ({out_zip!r}, {log!r}):
    if os.path.exists(stale):
        os.remove(stale)
zipfile.ZipFile({zip!r}).extractall(root)
os.remove({zip!r})
os.chdir(root)
subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y', '-q', *{remove!r}], capture_output=True)
pip = subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', *{packages!r}], capture_output=True, text=True)
if pip.returncode != 0:
    print(pip.stdout[-2000:], pip.stderr[-2000:], flush=True)
    raise SystemExit('pip install failed')
'''

REMOTE_ARCHIVE = '''
import os, zipfile
print({started!r}, flush=True)
root = {root!r}
if os.path.isdir(os.path.join(root, {out_dir!r})):
    # Model weights do not compress; store them as-is so the archive takes seconds, not minutes.
    with zipfile.ZipFile({out_zip!r}, 'w', zipfile.ZIP_STORED) as zf:
        for dirpath, _, filenames in os.walk(os.path.join(root, {out_dir!r})):
            for filename in filenames:
                full = os.path.join(dirpath, filename)
                zf.write(full, os.path.relpath(full, root))
    print('archived', {out_dir!r}, f'({{os.path.getsize({out_zip!r}) / 1e9:.1f}} GB)')
else:
    print('nothing to download:', {out_dir!r}, 'was not created')
print({ok!r})
'''

REMOTE_RUN = REMOTE_SETUP + '''
proc = subprocess.Popen([sys.executable, '-u', 'main.py', *{args!r}], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
for line in proc.stdout:
    print(line, end='', flush=True)
if proc.wait() != 0:
    raise SystemExit(f'main.py exited with {{proc.returncode}}')
print({ok!r})
'''

# The model server outlives this cell: detached from the kernel and polled until /health answers.
REMOTE_MODEL = REMOTE_SETUP + '''
import urllib.request
proc = subprocess.Popen([sys.executable, '-u', 'main.py', *{args!r}], stdout=open({log!r}, 'w'),
                        stderr=subprocess.STDOUT, start_new_session=True)
with open({log!r}) as tail:
    while True:
        print(tail.read(), end='', flush=True)
        if proc.poll() is not None:
            raise SystemExit(f'model server exited with {{proc.returncode}}')
        try:
            urllib.request.urlopen('http://127.0.0.1:{port}/health', timeout=2)
            break
        except OSError:
            time.sleep(2)
    print(tail.read(), end='', flush=True)
print('model server ready on port {port}')
print({ok!r})
'''


class RemoteError(RuntimeError):
    pass


class ColabRunner:

    def __init__(self, config, root):
        self.config = config
        self.root = root
        self.export = os.path.join(root, EXPORT_DIR)
        self.colab_path = shutil.which('colab')
        if self.colab_path is None:
            raise SystemExit("the 'colab' CLI is not installed: pip install google-colab-cli  "
                             "(or run everything on this machine with --local)")
        os.makedirs(self.export, exist_ok=True)
        # Piped stdout defaults to cp1252 on Windows, which cannot encode progress-bar glyphs from the VM.
        self.env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
        bundle = self.ca_bundle()
        if bundle:
            self.env.update(REQUESTS_CA_BUNDLE=bundle, SSL_CERT_FILE=bundle, CURL_CA_BUNDLE=bundle)

    def render(self, template, **values):
        remote_env = {key: os.environ[key] for key in REMOTE_ENV if os.environ.get(key)}
        return template.format(root=REMOTE_ROOT, zip=REMOTE_ZIP, out_zip=REMOTE_OUT_ZIP, log=REMOTE_LOG,
                               ok=REMOTE_OK, started=REMOTE_STARTED, packages=list(REMOTE_PACKAGES),
                               remove=list(REMOTE_REMOVE), env=remote_env, **values)

    # --- local environment ---

    def ca_bundle(self):
        # The CLI only trusts certifi; behind a TLS-inspecting proxy the extra CA lives in the OS store (Windows).
        if os.environ.get('REQUESTS_CA_BUNDLE') or not hasattr(ssl, 'enum_certificates'):
            return None
        pems = []
        try:
            import certifi
            with open(certifi.where(), encoding='ascii') as f:
                pems.append(f.read())
        except ImportError:
            pass
        for store in ('ROOT', 'CA'):
            for der, encoding, trust in ssl.enum_certificates(store):
                if encoding == 'x509_asn' and (trust is True or (isinstance(trust, set) and SERVER_AUTH_OID in trust)):
                    pems.append(ssl.DER_cert_to_PEM_cert(der))
        path = os.path.join(self.export, CA_BUNDLE_FILE)
        with open(path, 'w', encoding='ascii') as f:
            f.write('\n'.join(pems))
        return path

    def ssh_key(self):
        ssh_dir = os.path.expanduser('~/.ssh')
        if any(os.path.exists(os.path.join(ssh_dir, name)) for name in SSH_KEYS):
            return
        os.makedirs(ssh_dir, exist_ok=True)
        key = os.path.join(ssh_dir, SSH_KEYS[0])
        print(f"creating SSH key {key} for the Colab tunnel")
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', key], check=True)

    # --- colab CLI ---

    def colab(self, *args, **kwargs):
        command = [self.colab_path, *args]
        print('$', ' '.join(command), flush=True)
        return subprocess.run(command, check=True, env=self.env, **kwargs)

    def session(self, *args, **kwargs):
        return self.colab(*args[:1], '-s', self.config.session, *args[1:], **kwargs)

    def sessions(self):
        output = subprocess.run([self.colab_path, 'sessions'], capture_output=True, text=True, env=self.env).stdout
        return re.findall(SESSION_LINE, output, re.MULTILINE)

    def stop_others(self):
        # The free tier allows a single session.
        for name in self.sessions():
            if self.config.reuse and name == self.config.session:
                continue
            print(f"stopping leftover session '{name}'")
            subprocess.run([self.colab_path, 'stop', '-s', name], env=self.env)

    def create(self):
        cfg = self.config
        args = ['new', '-s', cfg.session]
        if cfg.gpu:
            args += ['--gpu', cfg.gpu]
        self.colab(*args)

    def deploy(self):
        source = os.path.join(self.export, LOCAL_ZIP)
        count = zip_dir(self.root, source, ARCHIVE_EXCLUDE)
        size_mb = os.path.getsize(source) / 1e6
        print(f"packed {count} files ({size_mb:.1f} MB)")
        if size_mb > ARCHIVE_MAX_MB:
            raise SystemExit(f"archive is {size_mb:.0f} MB; expected a few MB of source. Something large is in the project "
                             f"folder (a virtualenv, model weights?). Add it to ARCHIVE_EXCLUDE in common/constants.py.")
        self.stop_others()
        if not self.config.reuse:
            try:
                self.create()
            except subprocess.CalledProcessError:
                raise SystemExit("could not allocate a runtime: Colab refused (usage or capacity limit); "
                                 "wait and retry, try --gpu='' for a CPU runtime, or use --local")
        for attempt in range(1, UPLOAD_RETRIES + 1):
            try:
                self.session('upload', source, REMOTE_ZIP)
                break
            except subprocess.CalledProcessError:
                # A fresh runtime's hostname can take a while to resolve; the CLI gives up immediately.
                if attempt == UPLOAD_RETRIES:
                    self.release()
                    raise SystemExit('upload failed; the runtime never became reachable')
                print(f"runtime not reachable yet, retrying in {RETRY_DELAY}s ({attempt}/{UPLOAD_RETRIES})", flush=True)
                time.sleep(RETRY_DELAY)

    def exec(self, script, retries=3):
        command = [self.colab_path, 'exec', '-s', self.config.session, '--timeout', str(self.config.remote_timeout)]
        for attempt in range(1, retries + 1):
            print('$', ' '.join(command), flush=True)
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace',
                                       env=self.env)
            process.stdin.write(script)
            process.stdin.close()
            ok, started, output = False, False, []
            for line in process.stdout:
                if REMOTE_OK in line:
                    ok = True
                elif REMOTE_STARTED in line:
                    started = True
                else:
                    output.append(line)
                    print(line, end='', flush=True)
            if process.wait() == 0 and ok:
                return
            # The kernel's websocket is flaky right after provisioning; only retry if our script never began.
            transient = not started and any(marker in ''.join(output) for marker in TRANSIENT_ERRORS)
            if not transient or attempt == retries:
                raise RemoteError('remote command failed')
            print(f"kernel not ready, retrying in {RETRY_DELAY}s ({attempt}/{retries})", flush=True)
            time.sleep(RETRY_DELAY)

    def download(self):
        out_dir = self.config.out_dir
        archive = os.path.join(self.export, os.path.basename(REMOTE_OUT_ZIP))
        print(f"downloading {out_dir} (several GB)", flush=True)
        self.exec(self.render(REMOTE_ARCHIVE, out_dir=out_dir))
        try:
            self.session('download', REMOTE_OUT_ZIP, archive)
        except subprocess.CalledProcessError:
            print(f"no output archive to download for {out_dir}")
            return
        target = os.path.join(self.root, out_dir)
        shutil.rmtree(target, ignore_errors=True)
        shutil.unpack_archive(archive, self.root)
        os.remove(archive)
        print(f"downloaded to {target}; `python main.py --local` will use it")

    def release(self):
        if self.config.keep:
            print(f"session '{self.config.session}' kept running; stop it with: colab stop -s {self.config.session}")
        else:
            self.session('stop')

    # --- commands ---

    def remote_args(self, command, flags):
        # --local stops the VM from trying to reach Colab itself; --platform makes the tool prompt describe this OS.
        passthrough = [f for f in flags if not f.startswith(('--local', '--model_url=', '--platform=', '--text', '--tui'))]
        return [command, '--local', f'--platform={self.config.platform_name()}', *passthrough]

    def run(self, command, flags):
        if command == 'talk':
            return self.talk(flags)
        self.deploy()
        try:
            self.exec(self.render(REMOTE_RUN, args=self.remote_args(command, flags)))
            if self.config.hf_repo:
                print(f"adapter is on the Hub as {self.config.hf_repo}; Colab runs will load it from there")
            else:
                self.download()
        finally:
            self.release()

    def tunnel(self, port):
        if port_in_use(MODEL_HOST, port):
            raise SystemExit(f"port {port} on this machine is already in use; talk would connect to that instead of Colab. "
                             f"Stop whatever listens there or pass --model_port=<other>.")
        proxy = [self.colab_path, 'ssh', '--proxy-mode', '-s', self.config.session]
        proxy = subprocess.list2cmdline(proxy) if os.name == 'nt' else shlex.join(proxy)
        options = [f'ProxyCommand={proxy}', f'UserKnownHostsFile={os.devnull}', *SSH_OPTIONS]
        command = ['ssh', '-N', *(flag for option in options for flag in ('-o', option)),
                   '-L', f'{port}:127.0.0.1:{port}', SSH_HOST]
        print('$', ' '.join(command), flush=True)
        process = subprocess.Popen(command, env=self.env)
        if not wait_for_health(f'http://{MODEL_HOST}:{port}', process, attempts=60):
            process.terminate()
            raise SystemExit('ssh tunnel did not come up')
        return process

    def talk(self, flags):
        # Model on the GPU VM; assistant, voice and every tool on this machine, talking over an SSH tunnel.
        if shutil.which('ssh') is None:
            raise SystemExit("'ssh' is not installed (on Windows enable the OpenSSH Client optional feature)")
        port = self.config.model_port
        self.ssh_key()
        self.deploy()
        tunnel = None
        try:
            self.exec(self.render(REMOTE_MODEL, args=self.remote_args('model', flags), port=port))
            tunnel = self.tunnel(port)
            local = [sys.executable, 'main.py', 'talk', f'--model_url=http://{MODEL_HOST}:{port}', *flags]
            print('$', ' '.join(local), flush=True)
            subprocess.run(local, cwd=self.root)
        except KeyboardInterrupt:
            print('\nstopping')
        finally:
            if tunnel is not None and tunnel.poll() is None:
                tunnel.terminate()
            if not self.config.keep and not self.config.hf_repo:
                print("note: the trained adapter stays on the VM and is lost when it stops; "
                      "set HF_REPO in .env so it is pushed to the Hub, or run `python main.py finetune` to download it")
            try:
                self.release()
            except KeyboardInterrupt:
                self.release()
