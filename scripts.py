import json, glob, os
HERE = os.path.dirname(os.path.abspath(__file__))
VIDEOS = {os.path.basename(f)[:-5]: json.load(open(f)) for f in sorted(glob.glob(os.path.join(HERE, "specs", "*.json")))}
