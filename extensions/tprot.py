import subprocess

def tprot(text):
    """Convert using t-prot utility"""
    try:
        pipe = subprocess.Popen(['t-prot', '-t', '-s', '--body'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        stdout, stderr = pipe.communicate(input=str(text))
        text._value = stdout
        return text.hyperlinked()
    except Exception as ex:
        return text.hyperlinked()

def init(instance):
    instance.registerUtil('tprot', tprot)
