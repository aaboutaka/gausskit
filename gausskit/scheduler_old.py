import os
import time
import subprocess
from prompt_toolkit.completion import WordCompleter, PathCompleter
from gausskit.completions import tab_autocomplete_prompt, HybridCompleter
import smtplib
from email.message import EmailMessage


class GaussianJobScheduler:
    def __init__(self, gs_input, es_input, fc_input, poll_interval=5,
                 nproc=56, partition='medium', time_limit='23:50:00',
                 gdv='gdvj30+', email_notify=False, email_address=None):
        self.gs_input = gs_input
        self.es_input = es_input
        self.fc_input = fc_input
        self.poll_interval = poll_interval
        self.nproc = nproc
        self.partition = partition
        self.time_limit = time_limit
        self.gdv = gdv
        self.email_notify = email_notify
        self.email_address = email_address

    def submit_job(self, input_file):
        if not os.path.exists(f"{input_file}.com"):
            print(f"❌ Missing input file: {input_file}.com")
            return False
        cmd = [
            "Hgbatch",
            "-n", str(self.nproc),
            "-p", self.partition,
            "-t", self.time_limit,
            "--gdv", self.gdv,
            f"{input_file}.com"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Submitted {input_file}.com → {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Failed to submit {input_file}.com:\n{result.stderr.strip()}")
            return False

    def check_log_tail(self, filename, keyword, lines=50):
        if not os.path.exists(filename):
            return False
        try:
            with open(filename, 'rb') as f:
                f.seek(0, os.SEEK_END)
                f_size = f.tell()
                f.seek(max(f_size - 2048, 0), os.SEEK_SET)  # Read last ~2KB
                tail = f.read().decode(errors='ignore').splitlines()
                return any(keyword in line for line in tail[-lines:])
        except Exception as e:
            print(f"⚠️ Error checking {filename}: {e}")
            return False

    def wait_for_completion(self, label, files_keywords):
        print(f"⏳ Waiting for {label} jobs to complete...")
        while True:
            all_done = all(self.check_log_tail(f"{f}.log", keyword)
                           for f, keyword in files_keywords)
            if all_done:
                print(f"✅ {label} jobs finished.")
                break
            time.sleep(self.poll_interval)

    def send_email_notification(self):
        if not self.email_address:
            return
        try:
            msg = EmailMessage()
            msg.set_content("All Gaussian jobs (GS, ES, FC) completed successfully.")
            msg["Subject"] = "Gaussian Job Notification"
            msg["From"] = self.email_address
            msg["To"] = self.email_address
    
            # Gmail SMTP setup
            import ssl
            smtp_server = "smtp.gmail.com"
            smtp_port = 465
            sender_email = self.email_address
            password = tab_autocomplete_prompt("Enter your email password (App Password if 2FA): ")
    
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
                server.login(sender_email, password)
                server.send_message(msg)
    
            print(f"📧 Email sent to {self.email_address}")
        except Exception as e:
            print(f"⚠️ Email failed: {e}")
    

    def run(self):
        if not (self.submit_job(self.gs_input) and self.submit_job(self.es_input)):
            print("❌ Failed to submit GS or ES job.")
            return

        self.wait_for_completion("GS and ES", [
            (self.gs_input, "Normal termination"),
            (self.es_input, "Normal termination")
        ])

        if self.submit_job(self.fc_input):
            print("🚀 FC job submitted after GS/ES → waiting for FC to finish...")
            self.wait_for_completion("FC", [
                (self.fc_input, "Final Spectrum")
            ])
            print("✅ FC job finished.")
        else:
            print("❌ Failed to submit FC job.")

        if self.email_notify:
            self.send_email_notification()


def run_job_scheduler():
    print("=" * 60)
    print("Job Scheduler: Ground → Excited → Franck–Condon")
    print("=" * 60)

    com_files = [f for f in os.listdir() if f.endswith(".com")]
    hybrid = HybridCompleter([
        WordCompleter(com_files),
        PathCompleter(file_filter=lambda f: f.endswith(".com"))
    ])

    gs_input = tab_autocomplete_prompt("Ground state .com file: ", completer=hybrid).strip().removesuffix(".com")
    es_input = tab_autocomplete_prompt("Excited state .com file: ", completer=hybrid).strip().removesuffix(".com")
    fc_input = tab_autocomplete_prompt("Franck–Condon .com file: ", completer=hybrid).strip().removesuffix(".com")

    # Optional email
    use_email = tab_autocomplete_prompt("Send email upon completion? (y/n): ").lower().startswith('y')
    email = None
    if use_email:
        email = tab_autocomplete_prompt("Enter your email address: ").strip()

    scheduler = GaussianJobScheduler(
        gs_input, es_input, fc_input,
        poll_interval=5,
        email_notify=use_email,
        email_address=email
    )
    scheduler.run()




