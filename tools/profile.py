"""Game profiles: games/<id>/game.toml, the one place for game-specific values.

    python3 -I tools/profile.py                 list the profiles (id, title, status, executable)
    python3 -I tools/profile.py jackass         print one profile as JSON (for shell scripts: jq)
    python3 -I tools/profile.py jackass executable.name    one value

As a module: profile.load('jackass') -> dict, profile.all_profiles() -> [dict].
Python 3.11+ (tomllib).
"""
import json
import os
import sys
import tomllib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GAMES = os.path.join(ROOT, 'games')


def load(game_id):
    path = os.path.join(GAMES, game_id, 'game.toml')
    with open(path, 'rb') as f:
        prof = tomllib.load(f)
    prof.setdefault('id', game_id)
    prof['_path'] = path
    return prof


def all_profiles():
    out = []
    for name in sorted(os.listdir(GAMES)):
        if os.path.isfile(os.path.join(GAMES, name, 'game.toml')):
            out.append(load(name))
    return out


def by_executable(elf_name):
    for prof in all_profiles():
        if prof['executable']['name'].upper() == elf_name.upper():
            return prof
    return None


def get(prof, dotted):
    cur = prof
    for part in dotted.split('.'):
        cur = cur[part]
    return cur


def main(argv):
    if len(argv) == 1:
        for p in all_profiles():
            print(f"{p['id']:10} {p['status']:12} {p['executable']['name']:12} {p['title']}")
        return
    prof = load(argv[1])
    if len(argv) >= 3:
        value = get(prof, argv[2])
        print(value if isinstance(value, str) else json.dumps(value))
    else:
        print(json.dumps({k: v for k, v in prof.items() if not k.startswith('_')}, indent=1))


if __name__ == '__main__':
    main(sys.argv)
