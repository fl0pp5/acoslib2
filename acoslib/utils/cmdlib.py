import logging
import subprocess


def runcmd(cmd: str, quite: bool = False) -> subprocess.CompletedProcess:
    if not quite:
        logging.info(f"start command :: `{cmd}`")

    try:
        cp = subprocess.run(cmd,
                            shell=True,
                            capture_output=True,
                            check=True)
    except subprocess.CalledProcessError as e:
        if e.stdout:
            logging.error(f" STDOUT :: {e.stdout.decode()}")
        if e.stderr:
            logging.error(f" STDERR :: {e.stderr.decode()}")

        raise e

    if not quite:
        logging.info(f" STDOUT :: {cp.stdout.decode()}")
        logging.info(f" STDERR :: {cp.stderr.decode()}")

    return cp

