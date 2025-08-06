# gausskit/scheduler.py

import os, re
import sys
import time
import subprocess
import smtplib
import ssl
import getpass
from email.message import EmailMessage
import signal

from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter, PathCompleter

from gausskit.completions import tab_autocomplete_prompt, HybridCompleter
from .generator import create_default_fc_input


def daemonize(logfile="gausskit-scheduler.log"):
    """
    Fork this process into a background daemon and redirect stdout/stderr
    into `logfile`.  Returns True in the daemon, False in the parent.
    """
    if os.fork() > 0:
        return False
    os.setsid()
    if os.fork() > 0:
        os._exit(0)
    # Ignore SIGHUP (like nohup does)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)

    fd = os.open(logfile, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o644)
    os.dup2(fd, sys.stdout.fileno())
    os.dup2(fd, sys.stderr.fileno())
    os.close(fd)
    return True


class GaussianJobScheduler:
    """
    Orchestrates submission of Gaussian (.com) jobs via submit_cmd:
      - Chain mode (GS→ES→FC)
      - Single-job mode
      - Batch mode (all .com without .log)
    Supports SLURM-partition quota/fallback, background running,
    and email notification listing each Job ID.
    """

    def __init__(
        self,
        gs_input,
        es_input,
        fc_input,
        poll_interval=10,
        submit_cmd="Hgbatch",
        nproc=56,
        partition="medium",
        time_limit="23:50:00",
        gdv="gdvj30+",
        email_notify=False,
        email_address=None,
        email_password=None,
        quota_enabled=False,
        primary_part="medium",
        max_primary=2,
        fallback_part=None,
        wait_for_slot=True,
    ):
        # --- job inputs & SLURM settings ---
        self.gs_input = gs_input
        self.es_input = es_input
        self.fc_input = fc_input
        self.poll_interval = poll_interval
        self.nproc = nproc
        self.partition = partition
        self.time_limit = time_limit
        self.gdv = gdv
        self.submit_cmd = submit_cmd

        # --- email notification settings ---
        self.email_notify = email_notify
        self.email_address = email_address
        self.email_password = email_password

        # --- quota/fallback parameters ---
        self.quota_enabled = quota_enabled
        self.primary_part = primary_part
        self.max_primary = max_primary
        self.fallback_part = fallback_part
        self.wait_for_slot = wait_for_slot

        # will collect (basename, jobid) for email
        self.submitted_jobs = []

    def count_user_jobs(self, partition):
        """
        Return how many jobs this user currently has in a given SLURM partition.
        """
        user = getpass.getuser()
        res = subprocess.run(
            ["squeue", "-u", user, "-h", "-p", partition],
            capture_output=True,
            text=True,
        )
        # count only non-blank lines
        return len([L for L in res.stdout.splitlines() if L.strip()])

    def _choose_partition(self):
        """
        Pick a partition for submission:
          - If quota is disabled: return `self.partition`
          - If primary has slots: return primary
          - Else if fallback defined: return fallback
          - Else if wait_for_slot: block until primary has a slot
          - Else: return primary anyway
        """
        if not self.quota_enabled:
            return self.partition

        # 1) try primary if under quota
        if self.count_user_jobs(self.primary_part) < self.max_primary:
            return self.primary_part

        # 2) primary full → use fallback immediately if available
        if self.fallback_part:
            return self.fallback_part

        # 3) no fallback → either wait or go ahead on primary
        if self.wait_for_slot:
            print(f"⏳ Partition '{self.primary_part}' is full; waiting for slot…")
            while True:
                time.sleep(self.poll_interval)
                if self.count_user_jobs(self.primary_part) < self.max_primary:
                    print(f"✅ Slot freed in '{self.primary_part}'.")
                    return self.primary_part
        # fallback to primary without waiting
        return self.primary_part


    def submit_job(self, input_base):
        """
        Submit `input_base`.com via submit_cmd, retrying across partitions until
        we get a numeric Job ID (or indefinitely if wait_for_slot=True).
        Returns the Job ID string, or None if the submission itself fails.
        """
        com = f"{input_base}.com"
        if not os.path.exists(com):
            print(f"❌ Missing input file: {com}")
            return None
    
        # Build list of partitions to attempt, in order
        parts = []
        if self.quota_enabled:
            parts.append(self.primary_part)
            if self.fallback_part:
                parts.append(self.fallback_part)
        else:
            parts.append(self.partition)
        # remove duplicates
        seen = set()
        parts = [p for p in parts if not (p in seen or seen.add(p))]
    
        while True:
            for part in parts:
                if self.quota_enabled and part == self.primary_part:
                    cnt = self.count_user_jobs(part)
                    if cnt >= self.max_primary:
                        print(f"⚠️ Primary '{part}' full ({cnt}/{self.max_primary}), skipping.")
                        continue
    
                if self.submit_cmd.lower() == "hgbatch":
                    cmd = [
                        "Hgbatch",
                        "-n", str(self.nproc),
                        "-p", part,
                        "-t", self.time_limit,
                        "--gdv", self.gdv,
                        com,
                    ]
                elif self.submit_cmd.lower() == "gsub":
                    cmd = [
                        "gsub",
                        "-n", str(self.nproc),
                        "-p", part,
                        "-t", self.time_limit,
                        com,
                    ]
                else:  # direct g16 call or fallback
                    cmd = [self.submit_cmd, com]
    
                result = subprocess.run(cmd, capture_output=True, text=True)
    
                if result.returncode != 0:
                    print(f"❌ Submission failed (return code ≠ 0) on '{part}':\n{result.stderr.strip()}")
                    return None
    
                match = re.search(r"\b(\d+)\b", result.stdout)
                jobid = match.group(1) if match else None

                stderr_lower = result.stderr.lower()
                if "error" in stderr_lower or "qos" in stderr_lower or "limit" in stderr_lower:
                    print(f"❌ Submission error in stderr on '{part}':\n{result.stderr.strip()}")
                    return None
    
                if not jobid or jobid in {"0", "00"}:
                    print(f"⚠️ Invalid or missing Job ID from stdout:\n{result.stdout.strip()}")
                    print(f"⚠️ STDERR output was:\n{result.stderr.strip()}")
                    print(f"⚠️ Command used: {' '.join(cmd)}")
                else:
                    print(f"✅ Submitted {com} → Job ID {jobid} (partition={part})")
                    if jobid and jobid.isdigit() and jobid not in {"0", "00"}:
                        self.submitted_jobs.append((input_base, jobid))

                    return jobid
    
            if not self.wait_for_slot:
                print("❌ All partitions full (and wait_for_slot=False). Aborting.")
                return None
    
            print(f"⏳ Waiting {self.poll_interval}s before retrying submissions…")
            time.sleep(self.poll_interval)


#    def submit_job(self, input_base):
#        """
#        Submit `input_base`.com via submit_cmd, retrying across partitions until
#        we get a numeric Job ID (or indefinitely if wait_for_slot=True).
#        Returns the Job ID string, or None if the submission itself fails.
#        """
#        com = f"{input_base}.com"
#        if not os.path.exists(com):
#            print(f"❌ Missing input file: {com}")
#            return None
#
#        # Build list of partitions to attempt, in order
#        parts = []
#        if self.quota_enabled:
#            parts.append(self.primary_part)
#            if self.fallback_part:
#                parts.append(self.fallback_part)
#        else:
#            parts.append(self.partition)
#        # remove duplicates
#        seen = set()
#        parts = [p for p in parts if not (p in seen or seen.add(p))]
#
#        # loop until we either succeed or give up
#        while True:
#            for part in parts:
#                # enforce quota on primary
#                if self.quota_enabled and part == self.primary_part:
#                    cnt = self.count_user_jobs(part)
#                    if cnt >= self.max_primary:
#                        print(f"⚠️ Primary '{part}' full ({cnt}/{self.max_primary}), skipping.")
#                        continue
#
#                if self.submit_cmd.lower() == "hgbatch":
#                    cmd = [
#                        "Hgbatch",
#                        "-n", str(self.nproc),
#                        "-p", part,
#                        "-t", self.time_limit,
#                        "--gdv", self.gdv,
#                        com,
#                    ]
#                elif self.submit_cmd.lower() == "gsub":
#                    cmd = [
#                        "gsub",
#                        "-n", str(self.nproc),
#                        "-p", part,
#                        "-t", self.time_limit,
#                        com,
#                    ]
#                else:  # direct g16 call or fallback
#                    cmd = [self.submit_cmd, com]
#                
#        #        cmd = [
#        #            "Hgbatch",
#        #            "-n",
#        #            str(self.nproc),
#        #            "-p",
#        #            part,
#        #            "-t",
#        #            self.time_limit,
#        #            "--gdv",
#        #            self.gdv,
#        #            com,
#        #        ]
#                result = subprocess.run(cmd, capture_output=True, text=True)
#
#                if result.returncode != 0:
#                    # Hgbatch itself errored out
#                    print(f"❌ Failed to submit {com} on '{part}':\n{result.stderr.strip()}")
#                    return None
#
#                # try to parse the last token as an integer Job ID
#                #out_tokens = result.stdout.strip().split()
#                #jobid = out_tokens[-1] if out_tokens and out_tokens[-1].isdigit() else None
#                match = re.search(r"\b(\d+)\b", result.stdout) 
#                jobid = match.group(1) if match else None
#
#                if not jobid:
#                    print(f"⚠️ No Job ID parsed from output:\n{result.stdout.strip()}")
#
#
#                if jobid:
#                    print(f"✅ Submitted {com} → Job ID {jobid} (partition={part})")
#                    self.submitted_jobs.append((input_base, jobid))
#                    return jobid
#                else:
#                    # no numeric ID → likely partition is full
#                    print(f"⚠️ No Job ID returned on '{part}' — partition probably full.")
#
#            # if we tried every partition without ID
#            if not self.wait_for_slot:
#                print("❌ All partitions full (and wait_for_slot=False). Aborting.")
#                return None
#
#            # wait then retry
#            print(f"⏳ Waiting {self.poll_interval}s before retrying submissions…")
#            time.sleep(self.poll_interval)

    def check_log_tail(self, base, keyword, lines=50):
        """
        Return True if any of the last `lines` of base.log contain `keyword`.
        """
        path = f"{base}.log"
        if not os.path.exists(path):
            return False
        try:
            with open(path, "rb") as f:
                f.seek(-2048, os.SEEK_END)
                tail = f.read().decode(errors="ignore").splitlines()
        except OSError:
            with open(path, "r", errors="ignore") as f:
                tail = f.readlines()[-lines:]
        return any(keyword in L for L in tail[-lines:])
    
    def log_terminated_successfully(self, base):
        path = f"{base}.log"
        if not os.path.exists(path):
            return False
        try:
            with open(path, "r", errors="ignore") as f:
                lines = f.readlines()[-100:]
        except:
            return False
    
        for line in lines:
            if "Normal termination" in line:
                return True
            if "Error termination" in line or "termination via Lnk1e" in line:
                print(f"❌ ERROR termination detected in {base}.log")
                return False
                
        return False

    
 
    def wait_for(self, label, checks):
        """
        Block until **all** (base, keyword) in `checks` are satisfied in the tail of their log file.
        If any log shows 'Error termination', abort immediately.
        """
        print(f"⏳ Waiting for {label} …")
        while True:
            all_done = True
            for base, keyword in checks:
                log_path = f"{base}.log"
                if not os.path.exists(log_path):
                    all_done = False
                    continue
    
                # Check for error termination first
                try:
                    with open(log_path, "rb") as f:
                        f.seek(-4096, os.SEEK_END)
                        tail = f.read().decode(errors="ignore").splitlines()
                except OSError:
                    with open(log_path, "r", errors="ignore") as f:
                        tail = f.readlines()[-100:]
    
                for line in tail:
                    if "Error termination" in line:
                        print(f"❌ ERROR termination detected in {base}.log")
                        self.send_email(
                            subject="❌ GaussKit: Job Failed",
                            body=f"Failure detected.\nCheck {base}.log.",
                            tail_log=f"{base}.log"
                        )
#                        self.send_email("GaussKit: Job Chain Failed ❌", f"Failure detected.\nCheck {base}.log.")

                        sys.exit(1)  # exit the program
    
                if not any(keyword in line for line in tail):
                    all_done = False
    
            if all_done:
                print(f"✅ {label} done.")
                return
    
            time.sleep(self.poll_interval)
    
    
    def send_email(self, subject=None, body=None, tail_log=None):
        """
        Send a summary email or a failure notice with optional log tail.
        """
        if not self.email_notify or not self.email_address:
            return
    
        msg = EmailMessage()
        msg["Subject"] = subject or "✅ GaussKit: Gaussian Jobs Completed"
        msg["From"] = self.email_address
        msg["To"] = self.email_address
    
        body_lines = []
    
        # Default success summary
        if not subject and not body:
            body_lines.append("Your Gaussian jobs have completed:")
            for name, jid in self.submitted_jobs:
                body_lines.append(f"  • {name}.com → Job ID: {jid}")
        else:
            body_lines.append(body or "(No message provided)")
    
        # Append log tail if requested
        if tail_log and os.path.exists(tail_log):
            body_lines.append("\n⏬ Tail of log file:")
            try:
                with open(tail_log, 'r', errors='ignore') as f:
                    tail = f.readlines()[-40:]  # adjust lines if needed
                    body_lines.extend(["    " + line.rstrip() for line in tail])
            except Exception as e:
                body_lines.append(f"(Failed to read log tail: {e})")
    
        msg.set_content("\n".join(body_lines))
    
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as s:
                s.login(self.email_address, self.email_password)
                s.send_message(msg)
            print(f"📧 Email sent to {self.email_address}")
        except Exception as e:
            print(f"⚠️ Failed to send email: {e}")
          
            
    def run_chain(self):
        print(f" Ground .com: {self.gs_input}")
        print(f" Excited .com: {self.es_input}")
        print(f" FC .com: {self.fc_input}")
    
        # Submit GS and ES jobs
        gid = self.submit_job(self.gs_input)
        eid = self.submit_job(self.es_input)
    
        if not gid or not eid:
            print("❌ One or both submissions failed.")
            return
    
        # Wait for GS and ES
        print("⏳ Waiting for GS and ES to finish...")
        self.wait_for("GS", [(self.gs_input, "Normal termination")])
        self.wait_for("ES", [(self.es_input, "Normal termination")])
    
        # Check GS
        gs_log = f"{self.gs_input}.log"
        if not self.log_terminated_successfully(self.gs_input):
            self.send_email(
                subject="❌ GaussKit: GS Job Failed",
                body=f"Failure detected in GS job: {gs_log}",
                tail_log=gs_log
            )
            print("❌ Halting chain due to GS failure.")
            return
    
        # Check ES
        es_log = f"{self.es_input}.log"
        if not self.log_terminated_successfully(self.es_input):
            self.send_email(
                subject="❌ GaussKit: ES Job Failed",
                body=f"Failure detected in ES job: {es_log}",
                tail_log=es_log
            )
            print("❌ Halting chain due to ES failure.")
            return
    
        # Submit FC job
        fid = self.submit_job(self.fc_input)
        if not fid:
            print("❌ FC submission failed.")
            return
    
        print("⏳ Waiting for FC to finish...")
        self.wait_for("FC", [(self.fc_input, "Normal termination")])
    
        # Check FC
        fc_log = f"{self.fc_input}.log"
        if not self.log_terminated_successfully(self.fc_input):
            self.send_email(
                subject="❌ GaussKit: FC Job Failed",
                body=f"Failure detected in FC job: {fc_log}",
                tail_log=fc_log
            )
            print("❌ FC job failed.")
            return
    
        # All successful
        print("✅ Job chain complete.")
        self.send_email()
    
    
#    def run_chain(self):
#        print(f" Ground .com: {self.gs_input}")
#        print(f" Excited .com: {self.es_input}")
#        print(f" FC .com: {self.fc_input}")
#    
#        # Submit GS and ES jobs
#        gid = self.submit_job(self.gs_input)
#        eid = self.submit_job(self.es_input)
#    
#        if not gid or not eid:
#            print("❌ One or both submissions failed.")
#            return
#    
#        # Define termination patterns
#        success_tag = "Normal termination"
#        fail_tags = [
#            "Error termination",
#            "Link1:  fatal error",
#            "Erroneous write",
#            "l9999.exe",
#        ]
#    
#    
#        def check_termination(logfile, label="Job"):
#            if not os.path.exists(logfile):
#                print(f"❌ {label} log file not found: {logfile}")
#                return False
#        
#            with open(logfile, 'r', encoding='utf-8', errors='ignore') as f:
#                content = f.read().lower()  # lowercase for case-insensitive matching
#        
#            success_tag = "normal termination"
#            fail_tags = [
#                "error termination",
#                "error termination via",
#                "link1:  fatal error",
#                "erroneous write",
#                "l9999.exe",
#                "ntrerr",
#                "galloc:  could not allocate",
#                "problem in reading the checkpoint file",
#                "segmentation violation",
#                "l1.exe"
#            ]
#        
#            if success_tag in content:
#                return True
#        
#            for tag in fail_tags:
#                if tag in content:
#                    print(f"❌ {label} failed — detected error pattern: '{tag}'")
#                    return False
#        
#            print(f"⚠️ {label} did not terminate normally and no specific error was found.")
#            return False
#        
#        # Wait for GS and ES
#        print("⏳ Waiting for GS and ES to finish...")
#        self.wait_for("GS", [(self.gs_input, "Normal termination")])
#        self.wait_for("ES", [(self.es_input, "Normal termination")])
# 
#        if not check_termination(f"{self.gs_input}.log", "GS"):
#            self.send_email("GaussKit: Job Chain Failed ❌", f"Failure detected in GS.\nCheck {self.gs_input}.log")
#            print("❌ Halting chain due to GS failure.")
#            return
#
#        if  not check_termination(f"{self.es_input}.log", "ES"):
#            self.send_email("GaussKit: Job Chain Failed ❌", f"Failure detected in ES.\nCheck {self.es_input}.log.")
#            print("❌ Halting chain due to ES failure.")
#            return
#
#    
#        # Submit FC job
#        fid = self.submit_job(self.fc_input)
#        if not fid:
#            print("❌ FC submission failed.")
#            return
#    
#        print("⏳ Waiting for FC to finish...")
#        self.wait_for("FC", [(self.fc_input, "Normal termination")])
# 
#        if not check_termination(f"{self.fc_input}.log", "FC"):
#            self.send_email("GaussKit: FC Job Failed ❌", f"Failure detected in FC log file: {self.fc_input}.log.")
#            print("❌ FC job failed.")
#            return
#    
#        print("✅ Job chain complete.")
#        self.send_email("GaussKit: Job Chain Complete ✅", "All jobs (GS, ES, FC) completed successfully.")

    

    
    def run_single(self, single_base):
        """Submit exactly one .com and wait for Normal termination."""
        jid = self.submit_job(single_base)
        if not jid:
            return
        self.wait_for("single job", [(single_base, "Normal termination")])
        if self.email_notify:
            self.send_email()

    def run_batch(self):
        """
        Submit every .com in cwd that lacks a .log, then wait for all
        to finish before optionally emailing.
        """
        bases = [f[:-4] for f in os.listdir() if f.endswith(".com")]
        todo = [b for b in bases if not os.path.exists(f"{b}.log")]
        
        if not todo:
            print("✅ No .com without .log to submit.")
            return

        # submit all at once
        for b in todo:
            self.submit_job(b)

        # then wait for all
        checks = [(b, "Normal termination") for b in todo]
        self.wait_for(f"{len(todo)} batch jobs", checks)

        if self.email_notify:
            self.send_email()

    def run(self, mode, single_input=None):
        """Dispatch to chain / single / batch based on `mode`."""
        if mode == "1":
            self.run_chain()
        elif mode == "2":
            self.run_single(single_input)
        else:
            self.run_batch()


def run_job_scheduler():
    """
    Interactive entry point for the scheduler.  Offers:
      1) GS→ES→FC chain
      2) Single .com
      3) Batch (.com without .log)
    Then prompts quota/fallback, email, background, etc.
    """
    print("=" * 60)
    print("   GaussKit Job Scheduler")
    print("=" * 60)

    modes = "[1] GS→ES→FC  [2] Single .com  [3] Batch (.com without .log)"
    mode = prompt(f"{modes}\nEnter choice [1–3] [default: 1]: ").strip() or "1"
    while mode not in ("1", "2", "3"):
        print("❌ Please enter 1, 2 or 3.")
        mode = prompt(f"{modes}\nEnter choice [1–3] [default: 1]: ").strip() or "1"

    single = None
    if mode == "2":
        coms = [f for f in os.listdir() if f.endswith(".com")]
        single = prompt(
            "Single .com to submit: ",
            completer=WordCompleter(coms, ignore_case=True)
        ).strip().removesuffix(".com")
        if not os.path.exists(f"{single}.com"):
            print(f"❌ {single}.com not found.")
            return

    # Quota / fallback?
    ans = prompt("Enable quota/fallback logic? (y/n) [default: n]: ").strip().lower() or "n"
    quota = ans.startswith("y")

    primary = "medium"
    maxp = 2
    fallback = None
    wait_slot = True
    if quota:
        primary = prompt(f"Primary partition [default: {primary}]: ").strip() or primary
        mp = prompt(f"Max jobs in primary [default: {maxp}]: ").strip() or str(maxp)
        maxp = int(mp)
        fallback = prompt(f"Fallback partition [default: {primary}]: ").strip() or primary
        ans2 = prompt("Wait for slot if full? (y/n) [default: y]: ").strip().lower() or "y"
        wait_slot = ans2.startswith("y")

    submit_cmd = prompt("Submission command (Hgbatch/gsub/g16) [default: Hgbatch]: ").strip() or "Hgbatch"
    nproc = prompt("Number of processors [default: 56]: ").strip() or "56"
    time_limit = prompt("Time limit (HH:MM:SS) [default: 23:50:00]: ").strip() or "23:50:00"


    # Email?
    ans = prompt("Email upon completion? (y/n) [default: n]: ").strip().lower() or "n"
    email = ans.startswith("y")
    e_addr = e_pass = None
    if email:
        e_addr = prompt(" Gmail address: ").strip()
        e_pass = getpass.getpass(" App Password (hidden): ")

    # Chain-mode FC input?
    gs = es = fc = single
    if mode == "1":
        ans = prompt("Generate default FC input? (y/n) [default: n]: ").strip().lower() or "n"
        use_def = ans.startswith("y")
        coms = [f for f in os.listdir() if f.endswith(".com")]
        gs = prompt(" Ground .com: ", completer=WordCompleter(coms)).strip().removesuffix(".com")
        es = prompt(" Excited .com: ", completer=WordCompleter(coms)).strip().removesuffix(".com")
        if use_def:
            fc = create_default_fc_input(gs, es)
        else:
            fc = prompt(" FC .com: ", completer=WordCompleter(coms)).strip().removesuffix(".com")
    # Background?
    ans = prompt("Run scheduler in background? (y/n) [default: n]: ").strip().lower() or "n"
    bg = ans.startswith("y")
    if bg and not daemonize():
        print("🚀 Scheduler is now running in background (see gausskit-scheduler.log).")
        return
    
    sched = GaussianJobScheduler(
        gs_input=gs,
        es_input=es,
        fc_input=fc,
        poll_interval=10,
        nproc=int(nproc),
        partition="medium",
        time_limit=time_limit,
        gdv="gdvj30+",
        email_notify=email,
        email_address=e_addr,
        email_password=e_pass,
        quota_enabled=quota,
        primary_part=primary,
        max_primary=maxp,
        fallback_part=fallback,
        wait_for_slot=wait_slot,
        submit_cmd=submit_cmd,
    )
    
    sched.run(mode, single_input=single)

