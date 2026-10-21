import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.samples import generate
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',default='.local/samples');generate(p.parse_args().output)
