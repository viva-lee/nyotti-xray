import argparse
import sys


def main(argv=None):
    p = argparse.ArgumentParser(prog='nyotti-xray', description='Replay and x-ray a public trade history.')
    p.add_argument('--env', help='path to a .env file with TYPESAFE_API_KEY (default: ./.env)')
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('fetch', help='download the release from the original link and verify its SHA-256')
    t = sub.add_parser('tape', help='check every fill against the BitMEX public tape (~25 GB streamed)')
    t.add_argument('--workers', type=int, default=8)
    sub.add_parser('build', help='derive decisions, account exposure and market context')
    j = sub.add_parser('judge', help='ask Jev the lens questions about every decision')
    j.add_argument('--lenses', default=None)
    j.add_argument('--limit', type=int, default=None, help='only judge the first N decisions')
    sub.add_parser('analyze', help='run every analysis and write site/data')
    s = sub.add_parser('serve', help='open the viewer on localhost')
    s.add_argument('--port', type=int, default=4343)
    s.add_argument('--no-open', action='store_true')
    a = p.parse_args(argv)

    if a.cmd == 'fetch':
        from .fetch import fetch
        fetch()
    elif a.cmd == 'tape':
        from . import load, tape
        tape.run(load.fills(), workers=a.workers)
    elif a.cmd == 'build':
        from . import build
        build.run()
    elif a.cmd == 'judge':
        from . import judge
        judge.run(env=a.env, lens_path=a.lenses, limit=a.limit)
    elif a.cmd == 'analyze':
        from . import analyze
        analyze.run()
    elif a.cmd == 'serve':
        from . import serve
        serve.run(a.port, open_browser=not a.no_open)
    return 0


if __name__ == '__main__':
    sys.exit(main())
