from __future__ import annotations  # аннотации как строки
from dataclasses import dataclass  # шаблоны структур данных


# тип токена: вид (NUMBER, IDENT, COMMAND и т.д.) и его строковое значение
@dataclass(frozen=True)
class Token:
    kind: str
    value: str


# мейн класс
class Tokenizer:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0  # текущая позиция в строке

    # возвращает список всех токенов в тексте
    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch.isspace():
                self.pos += 1
                continue
            if ch.isdigit():
                tokens.append(self._read_number())
                continue
            if ch.isalpha():
                tokens.append(self._read_identifier())
                continue
            if ch == "\\":
                tokens.append(self._read_command())
                continue
            # значения
            simple_tokens = {
                "+": "PLUS",
                "-": "MINUS",
                "*": "MUL",
                "/": "DIV",
                "^": "POW",
                "(": "LPAREN",
                ")": "RPAREN",
                "{": "LBRACE",
                "}": "RBRACE",
                "_": "UNDERSCORE",
            }
            if ch in simple_tokens:
                tokens.append(Token(simple_tokens[ch], ch))
                self.pos += 1
                continue
            raise ValueError(f"неизвестный символ: {ch}")
        tokens.append(Token("EOF", ""))
        return tokens

    # считывает число ( илипоследовательность цифр) начиная с текущей позиции
    def _read_number(self) -> Token:
        start = self.pos
        while self.pos < len(self.text) and self.text[self.pos].isdigit():
            self.pos += 1
        return Token("NUMBER", self.text[start : self.pos])

    # считывает переменную (последовательность букв и цифр)
    def _read_identifier(self) -> Token:
        start = self.pos
        while self.pos < len(self.text) and self.text[self.pos].isalnum():
            self.pos += 1
        return Token("IDENT", self.text[start : self.pos])

    # считывает команду LaTeX (после \): последовательность букв
    def _read_command(self) -> Token:
        self.pos += 1
        start = self.pos
        while self.pos < len(self.text) and self.text[self.pos].isalpha():
            self.pos += 1
        name = self.text[start : self.pos]
        if not name:
            raise ValueError("после обратного слеша должна идти команда")
        return Token("COMMAND", name)
