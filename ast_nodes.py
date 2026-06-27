from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction


# создаёт число, оборачивая int в fraction
def make_number(value: int | Fraction) -> "Number":
    if isinstance(value, Fraction):
        return Number(value)
    return Number(Fraction(value))


# базовый класс для всех узлов аст
class Expr:
    precedence = 100

    def diff(self, var: str, simplify: bool = True) -> "Expr":
        raise NotImplementedError

    def simplify(self) -> "Expr":
        return self

    def to_latex(self, parent_precedence: int = 0) -> str:
        raise NotImplementedError

    def _wrap(self, text: str, parent_precedence: int) -> str:
        if self.precedence < parent_precedence:
            return f"\\left({text}\\right)"
        return text


# узел для числа (хранится как fraction)
@dataclass(frozen=True)
class Number(Expr):
    value: Fraction
    precedence = 10

    def diff(self, var: str, simplify: bool = True) -> Expr:
        return make_number(0)

    def to_latex(self, parent_precedence: int = 0) -> str:
        if self.value.denominator == 1:
            return str(self.value.numerator)
        if self.value < 0:
            positive = Number(-self.value)
            return f"-{positive.to_latex()}"
        return f"\\frac{{{self.value.numerator}}}{{{self.value.denominator}}}"


# константа e — экспонента
@dataclass(frozen=True)
class ConstantE(Expr):
    precedence = 10

    def diff(self, var: str, simplify: bool = True) -> Expr:
        return make_number(0)

    def to_latex(self, parent_precedence: int = 0) -> str:
        return "e"


# переменная, например x или y
@dataclass(frozen=True)
class Variable(Expr):
    name: str
    precedence = 10

    def diff(self, var: str, simplify: bool = True) -> Expr:
        if self.name == var:
            return make_number(1)
        return make_number(0)

    def to_latex(self, parent_precedence: int = 0) -> str:
        return self.name


# унарный минус
@dataclass(frozen=True)
class Neg(Expr):
    expr: Expr
    precedence = 4

    def diff(self, var: str, simplify: bool = True) -> Expr:
        raw = Neg(self.expr.diff(var, simplify))
        if simplify:
            return raw.simplify()
        return raw

    def simplify(self) -> Expr:
        expr = self.expr.simplify()
        if isinstance(expr, Number):
            return Number(-expr.value)
        if isinstance(expr, Neg):
            return expr.expr.simplify()
        return Neg(expr)

    def to_latex(self, parent_precedence: int = 0) -> str:
        text = f"-{self.expr.to_latex(self.precedence)}"
        return self._wrap(text, parent_precedence)


# сложение
@dataclass(frozen=True)
class Add(Expr):
    left: Expr
    right: Expr
    precedence = 1

    def diff(self, var: str, simplify: bool = True) -> Expr:
        raw = Add(self.left.diff(var, simplify), self.right.diff(var, simplify))
        if simplify:
            return raw.simplify()
        return raw

    def simplify(self) -> Expr:
        left = self.left.simplify()
        right = self.right.simplify()
        if is_zero(left):
            return right
        if is_zero(right):
            return left
        if isinstance(right, Neg):
            return Sub(left, right.expr).simplify()
        if isinstance(left, Number) and isinstance(right, Number):
            return Number(left.value + right.value)
        return Add(left, right)

    def to_latex(self, parent_precedence: int = 0) -> str:
        text = f"{self.left.to_latex(self.precedence)}+{self.right.to_latex(self.precedence)}"
        return self._wrap(text, parent_precedence)


# вычитание
@dataclass(frozen=True)
class Sub(Expr):
    left: Expr
    right: Expr
    precedence = 1

    def diff(self, var: str, simplify: bool = True) -> Expr:
        raw = Sub(self.left.diff(var, simplify), self.right.diff(var, simplify))
        if simplify:
            return raw.simplify()
        return raw

    def simplify(self) -> Expr:
        left = self.left.simplify()
        right = self.right.simplify()
        if is_zero(right):
            return left
        if is_zero(left):
            return Neg(right).simplify()
        if left == right:
            return make_number(0)
        if isinstance(left, Number) and isinstance(right, Number):
            return Number(left.value - right.value)
        return Sub(left, right)

    def to_latex(self, parent_precedence: int = 0) -> str:
        text = f"{self.left.to_latex(self.precedence)}-{self.right.to_latex(self.precedence + 1)}"
        return self._wrap(text, parent_precedence)


# умножение
@dataclass(frozen=True)
class Mul(Expr):
    left: Expr
    right: Expr
    precedence = 2

    def diff(self, var: str, simplify: bool = True) -> Expr:
        raw = Add(
            Mul(self.left.diff(var, simplify), self.right),
            Mul(self.left, self.right.diff(var, simplify)),
        )
        if simplify:
            return raw.simplify()
        return raw

    def simplify(self) -> Expr:
        left = self.left.simplify()
        right = self.right.simplify()
        if is_zero(left) or is_zero(right):
            return make_number(0)
        if is_one(left):
            return right
        if is_one(right):
            return left
        if is_minus_one(left):
            return Neg(right).simplify()
        if is_minus_one(right):
            return Neg(left).simplify()
        if isinstance(left, Neg):
            return Neg(Mul(left.expr, right)).simplify()
        if isinstance(right, Neg):
            return Neg(Mul(left, right.expr)).simplify()
        if isinstance(left, Number) and isinstance(right, Number):
            return Number(left.value * right.value)
        return Mul(left, right)

    def to_latex(self, parent_precedence: int = 0) -> str:
        left_text = product_part(self.left)
        right_text = product_part(self.right)
        separator = ""
        if needs_mul_separator(left_text, right_text):
            separator = "\\cdot "
        text = f"{left_text}{separator}{right_text}"
        return self._wrap(text, parent_precedence)


# деление/дробь
@dataclass(frozen=True)
class Div(Expr):
    numerator: Expr
    denominator: Expr
    precedence = 2

    def diff(self, var: str, simplify: bool = True) -> Expr:
        top = Sub(
            Mul(self.numerator.diff(var, simplify), self.denominator),
            Mul(self.numerator, self.denominator.diff(var, simplify)),
        )
        bottom = Pow(self.denominator, make_number(2))
        raw = Div(top, bottom)
        if simplify:
            return raw.simplify()
        return raw

    def simplify(self) -> Expr:
        numerator = self.numerator.simplify()
        denominator = self.denominator.simplify()
        if is_zero(numerator):
            return make_number(0)
        if is_one(denominator):
            return numerator
        if numerator == denominator:
            return make_number(1)
        if isinstance(denominator, Neg):
            return Neg(Div(numerator, denominator.expr)).simplify()
        if isinstance(numerator, Number) and isinstance(denominator, Number):
            return Number(numerator.value / denominator.value)
        return Div(numerator, denominator)

    def to_latex(self, parent_precedence: int = 0) -> str:
        text = f"\\frac{{{self.numerator.to_latex()}}}{{{self.denominator.to_latex()}}}"
        return self._wrap(text, parent_precedence)


# возведение в степень
@dataclass(frozen=True)
class Pow(Expr):
    base: Expr
    exponent: Expr
    precedence = 3

    def diff(self, var: str, simplify: bool = True) -> Expr:
        base = self.base
        exponent = self.exponent
        if isinstance(base, ConstantE):
            raw = Mul(self, exponent.diff(var, simplify))
            if simplify:
                return raw.simplify()
            return raw
        if isinstance(exponent, Number):
            raw = Mul(
                Mul(exponent, Pow(base, Number(exponent.value - 1))),
                base.diff(var, simplify),
            )
            if simplify:
                return raw.simplify()
            return raw
        raw = Mul(
            self,
            Add(
                Mul(exponent.diff(var, simplify), Ln(base)),
                Div(Mul(exponent, base.diff(var, simplify)), base),
            ),
        )
        if simplify:
            return raw.simplify()
        return raw

    def simplify(self) -> Expr:
        base = self.base.simplify()
        exponent = self.exponent.simplify()
        if is_zero(exponent):
            return make_number(1)
        if is_one(exponent):
            return base
        if is_zero(base):
            return make_number(0)
        if is_one(base):
            return make_number(1)
        if (
            isinstance(base, Number)
            and isinstance(exponent, Number)
            and exponent.value.denominator == 1
        ):
            power = exponent.value.numerator
            return Number(base.value**power)
        return Pow(base, exponent)

    def to_latex(self, parent_precedence: int = 0) -> str:
        if isinstance(self.base, (Number, ConstantE, Variable, Function, Log)):
            base_text = self.base.to_latex(self.precedence)
        else:
            base_text = f"\\left({self.base.to_latex()}\\right)"
        text = f"{base_text}^{{{self.exponent.to_latex()}}}"
        return self._wrap(text, parent_precedence)


# тригонометрические и гиперболические функции (sin, cos, tan, ...)
@dataclass(frozen=True)
class Function(Expr):
    name: str
    arg: Expr
    precedence = 10

    def diff(self, var: str, simplify: bool = True) -> Expr:
        arg_diff = self.arg.diff(var, simplify)
        if self.name == "sin":
            raw = Mul(arg_diff, Cos(self.arg))
        elif self.name == "cos":
            raw = Neg(Mul(arg_diff, Sin(self.arg)))
        elif self.name == "tan":
            raw = Div(arg_diff, Pow(Cos(self.arg), make_number(2)))
        elif self.name == "cot":
            raw = Neg(Div(arg_diff, Pow(Sin(self.arg), make_number(2))))
        elif self.name == "sinh":
            raw = Mul(arg_diff, Function("cosh", self.arg))
        elif self.name == "cosh":
            raw = Mul(arg_diff, Function("sinh", self.arg))
        elif self.name == "tanh":
            raw = Div(
                arg_diff, Pow(Function("cosh", self.arg), make_number(2))
            )
        elif self.name == "coth":
            raw = Neg(
                Div(arg_diff, Pow(Function("sinh", self.arg), make_number(2)))
            )
        elif self.name == "exp":
            raw = Mul(arg_diff, Function("exp", self.arg))
        else:
            raise ValueError(f"неизвестная функция: {self.name}")
        if simplify:
            return raw.simplify()
        return raw

    def simplify(self) -> Expr:
        return Function(self.name, self.arg.simplify())

    def to_latex(self, parent_precedence: int = 0) -> str:
        text = f"\\{self.name}({self.arg.to_latex()})"
        return self._wrap(text, parent_precedence)


# натуральный логарифм
@dataclass(frozen=True)
class Ln(Expr):
    arg: Expr
    precedence = 10

    def diff(self, var: str, simplify: bool = True) -> Expr:
        raw = Div(self.arg.diff(var, simplify), self.arg)
        if simplify:
            return raw.simplify()
        return raw

    def simplify(self) -> Expr:
        arg = self.arg.simplify()
        if is_one(arg):
            return make_number(0)
        if isinstance(arg, ConstantE):
            return make_number(1)
        return Ln(arg)

    def to_latex(self, parent_precedence: int = 0) -> str:
        text = f"\\ln({self.arg.to_latex()})"
        return self._wrap(text, parent_precedence)


# логарифм по произвольному основанию
@dataclass(frozen=True)
class Log(Expr):
    base: Expr
    arg: Expr
    precedence = 10

    def diff(self, var: str, simplify: bool = True) -> Expr:
        raw = Div(
            self.arg.diff(var, simplify),
            Mul(self.arg, Ln(self.base)),
        )
        if simplify:
            return raw.simplify()
        return raw

    def simplify(self) -> Expr:
        return Log(self.base.simplify(), self.arg.simplify())

    def to_latex(self, parent_precedence: int = 0) -> str:
        text = f"\\log_{{{self.base.to_latex()}}}({self.arg.to_latex()})"
        return self._wrap(text, parent_precedence)


# сокращение для создания синуса
def Sin(arg: Expr) -> Function:
    return Function("sin", arg)


# сокращение для создания косинуса
def Cos(arg: Expr) -> Function:
    return Function("cos", arg)


# проверяет, равен ли узел нулю
def is_zero(expr: Expr) -> bool:
    return isinstance(expr, Number) and expr.value == 0


# проверяет, равен ли узел единице
def is_one(expr: Expr) -> bool:
    return isinstance(expr, Number) and expr.value == 1


# проверяет, равен ли узел минус единице
def is_minus_one(expr: Expr) -> bool:
    return isinstance(expr, Number) and expr.value == -1


# оборачивает слагаемое в скобки если оно нужно для произведения
def product_part(expr: Expr) -> str:
    if isinstance(expr, (Add, Sub, Neg)):
        return f"\\left({expr.to_latex()}\\right)"
    return expr.to_latex(Mul.precedence)


# определяет, нужен ли cdot между множителями в латеехе
def needs_mul_separator(left_text: str, right_text: str) -> bool:
    if not left_text or not right_text:
        return False
    left_last = left_text[-1]
    if right_text.startswith("\\frac"):
        return left_last.isalnum() or left_last == "}"
    return (left_last.isalnum() or left_last == "}") and right_text[0].isdigit()