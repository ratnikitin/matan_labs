from __future__ import annotations
import argparse
import sys
from latex_parser import parse_latex
from tokenizer import Tokenizer


# берёт производную order раз и каждый раз упрощает
def nth_derivative(expr, var: str, order: int, simplify: bool = True):
    result = expr
    for _ in range(order):
        # делаем diff, потом условно упрощаем
        result = result.diff(var, simplify=simplify)
        if simplify:
            result = result.simplify()
    return result


# настраивает аргументы командной строки
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="взятие производных у latex выражений",
    )
    parser.add_argument(
        "expression",
        nargs="?",
        help="выражение в latex, например \\sin(x^2+1)",
    )
    parser.add_argument(
        "--var",
        default="x",
        help="переменная, по которой берем производную",
    )
    parser.add_argument(
        "--order",
        type=int,
        default=1,
        help="порядок производной",
    )
    parser.add_argument(
        "--tokens",
        action="store_true",
        help="показать токены",
    )
    parser.add_argument(
        "--no-simplify",
        action="store_true",
        help="не упрощать результат (и промежуточные производные)",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    expression_text = args.expression
    if not expression_text:
        expression_text = input("введите выражение: ").strip()
    if args.order < 0:
        raise ValueError("порядок производной должен быть неотрицательным")
    simplify = not args.no_simplify
    if args.tokens:
        tokens = Tokenizer(expression_text).tokenize()
        print("токены:")
        for token in tokens:
            print(f"{token.kind:>10}  {token.value}")
        print()
    try:
        expr = parse_latex(expression_text, simplify=simplify)
        result = nth_derivative(expr, args.var, args.order, simplify=simplify)
    except ValueError as error:
        print(f"ошибка: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    print(result.to_latex())


if __name__ == "__main__":
    main()
