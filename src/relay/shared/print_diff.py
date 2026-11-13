from .styles import BLUE, CYAN, GREEN, RED, RESET, YELLOW


def print_diff(results):
    color_map = {
        "UNCHANGED": RESET,
        "MODIFIED": YELLOW,
        "MOVED": CYAN,
        "COPIED": BLUE,
        "ADDED": GREEN,
        "DELETED": RED,
    }
    print(f"\n{'ACTION':<12} | {'PATH':<30} | {'ORIGIN / DETAIL'}")
    print("-" * 65)
    for res in sorted(results, key=lambda x: x.action.name):
        color = color_map.get(res.action.name, RESET)
        origin = f"(from {res.origin_path})" if res.origin_path else ""
        print(f"{color}{res.action.name:<12}{RESET} | {res.path:<30} | {origin}")
