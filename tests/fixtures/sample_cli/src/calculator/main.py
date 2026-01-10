"""CLI entrypoint for the calculator."""

import argparse
import sys

from calculator import ops
from calculator.history import add_entry, get_history


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="calc",
        description="A simple calculator CLI",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add two numbers")
    add_parser.add_argument("a", type=float, help="First number")
    add_parser.add_argument("b", type=float, help="Second number")

    # Subtract command
    sub_parser = subparsers.add_parser("subtract", help="Subtract two numbers")
    sub_parser.add_argument("a", type=float, help="First number")
    sub_parser.add_argument("b", type=float, help="Second number")

    # Multiply command
    mul_parser = subparsers.add_parser("multiply", help="Multiply two numbers")
    mul_parser.add_argument("a", type=float, help="First number")
    mul_parser.add_argument("b", type=float, help="Second number")

    # Divide command
    div_parser = subparsers.add_parser("divide", help="Divide two numbers")
    div_parser.add_argument("a", type=float, help="First number")
    div_parser.add_argument("b", type=float, help="Second number")

    # History command
    subparsers.add_parser("history", help="Show command history")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "history":
        history = get_history()
        if not history:
            print("No history yet.")
        else:
            for entry in history:
                print(entry)
        return 0

    # Execute operation
    operation_map = {
        "add": ops.add,
        "subtract": ops.subtract,
        "multiply": ops.multiply,
        "divide": ops.divide,
    }

    op_func = operation_map[args.command]
    result = op_func(args.a, args.b)

    # Record in history
    add_entry(args.command, args.a, args.b, result)

    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
