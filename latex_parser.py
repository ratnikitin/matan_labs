from __future__ import annotations
from fractions import Fraction
from ast_nodes import (
    Add,
    ConstantE,
    Div,
    Expr,
    Function,
    Ln,
    Log,
    Mul,
    Neg,
    Number,
    Pow,
    Sub,
    Variable,
)
from tokenizer import Token, Tokenizer


SUPPORTED_FUNCTIONS = {
    "sin",
    "cos",
    "tan",
    "cot",
    "sinh",
    "cosh",
    "tanh",
    "coth",
    "exp",
    "ln",
}


# рекурсивный спуск по токенам, строит аст
class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    # входная точка парсера, ждёт конец файла после выражения
    def parse(self, simplify: bool = True) -> Expr:
        expr = self.parse_expression()
        self.expect("EOF")
        if simplify:
            return expr.simplify()
        return expr

    # парсит сложение/вычитание (самый низкий приоритет)
    def parse_expression(self) -> Expr:
        node = self.parse_term()
        while self.current().kind in {"PLUS", "MINUS"}:
            if self.match("PLUS"):
                node = Add(node, self.parse_term())
            else:
                self.expect("MINUS")
                node = Sub(node, self.parse_term())
        return node

    # парсит умножение/деление (приоритет выше чем +-)
    def parse_term(self) -> Expr:
        node = self.parse_power()
        while True:
            if self.match("MUL"):
                node = Mul(node, self.parse_power())
                continue
            if self.match("DIV"):
                node = Div(node, self.parse_power())
                continue
            if self._is_implicit_multiplication():
                node = Mul(node, self.parse_power())
                continue
            return node

    # парсит возведение в степень (правоассоциативно)
    def parse_power(self) -> Expr:
        node = self.parse_unary()
        if self.match("POW"):
            node = Pow(node, self.parse_power())
        return node

    # парсит унарный минус (рекурсивно, чтобы работало ---x)
    def parse_unary(self) -> Expr:
        if self.match("MINUS"):
            return Neg(self.parse_unary())
        return self.parse_primary()

    # парсит еденичное выражение: число, переменную, скобки или команду
    def parse_primary(self) -> Expr:
        token = self.current()
        if self.match("NUMBER"):
            return Number(Fraction(token.value))
        if self.match("IDENT"):
            if token.value == "e":
                return ConstantE()
            return Variable(token.value)
        if self.match("LPAREN"):
            expr = self.parse_expression()
            self.expect("RPAREN")
            return expr
        if self.match("LBRACE"):
            expr = self.parse_expression()
            self.expect("RBRACE")
            return expr
        if self.match("COMMAND"):
            return self.parse_command(token.value)
        raise ValueError(f"неожиданный токен: {token.kind} {token.value}")

    # разбирает лвтех команды вроде \frac, \sin, \log
    def parse_command(self, name: str) -> Expr:
        if name == "frac":
            numerator = self.parse_group_in_braces()
            denominator = self.parse_group_in_braces()
            return Div(numerator, denominator)
        if name == "log":
            self.expect("UNDERSCORE")
            base = self.parse_log_base()
            arg = self.parse_function_argument("log")
            return Log(base, arg)
        if name == "ln":
            return Ln(self.parse_function_argument(name))
        if name in SUPPORTED_FUNCTIONS:
            return Function(name, self.parse_function_argument(name))
        raise ValueError(f"неподдерживаемая команда: \\{name}")

    # парсит основание логарифма (может быть в скобках или без)
    def parse_log_base(self) -> Expr:
        if self.match("LBRACE"):
            expr = self.parse_expression()
            self.expect("RBRACE")
            return expr
        return self.parse_primary()

    # парсит выражение в фигурных скобках { ... }
    def parse_group_in_braces(self) -> Expr:
        self.expect("LBRACE")
        expr = self.parse_expression()
        self.expect("RBRACE")
        return expr

    # парсит аргумент функции в круглых скобках, например \sin(x)
    def parse_function_argument(self, name: str) -> Expr:
        if not self.match("LPAREN"):
            raise ValueError(f"для \\{name} нужны круглые скобки, например \\{name}(x)")
        expr = self.parse_expression()
        self.expect("RPAREN")
        return expr

    # возвращает текущий токен (не сдвигая позицию)
    def current(self) -> Token:
        return self.tokens[self.pos]

    # проверяет, совпадает ли текущий токен с ожидаемым, и если да — сдвигает позицию
    def match(self, kind: str) -> bool:
        if self.current().kind == kind:
            self.pos += 1
            return True
        return False

    # проверяет токен и сдвигает позицию, а если не совпал — кидает ошибку
    def expect(self, kind: str) -> Token:
        token = self.current()
        if token.kind != kind:
            raise ValueError(
                f"ожидался токен {kind}, а пришел {token.kind} {token.value}"
            )
        self.pos += 1
        return token

    # проверяет, можно ли считать неявное умножение (например 2x)
    def _is_implicit_multiplication(self) -> bool:
        return self.current().kind in {
            "NUMBER",
            "IDENT",
            "COMMAND",
            "LPAREN",
            "LBRACE",
        }


# главная функция токенизирует строку и парсит в аст
def parse_latex(text: str, simplify: bool = True) -> Expr:
    tokenizer = Tokenizer(text)
    tokens = tokenizer.tokenize()
    parser = Parser(tokens)
    return parser.parse(simplify=simplify)
